# Document Processing Queue Architecture

## Problema

El endpoint `POST /knowledge-bases/{id}/documents` actualmente procesa el documento de forma **síncrona**:

```
Cliente → API → Extracción → Chunking → Embeddings (N llamadas a OpenAI) → Respuesta
```

Con documentos grandes (200+ páginas, miles de chunks) y muchos usuarios simultáneos, esto genera:

- Timeouts HTTP (la petición dura minutos)
- Bloqueo del worker de FastAPI
- Sin posibilidad de reintentos si falla la llamada a OpenAI
- Sin visibilidad del progreso real

---

## Arquitectura propuesta

```
Cliente
  │
  ▼
POST /knowledge-bases/{id}/documents
  │  acepta el archivo, crea el Document con status=PENDING
  │  encola el job y retorna inmediatamente (202 Accepted)
  ▼
Cola (Redis / RabbitMQ / SQS)
  │
  ▼
Worker(s) asincrónicos (Celery / ARQ / Dramatiq)
  │  consume el job
  │  PENDING → PROCESSING
  │  extrae texto del archivo
  │  genera chunks
  │  llama a OpenAI por cada chunk (con retry)
  │  actualiza chunks_processed / chunks_total en DB
  │  PROCESSING → PROCESSED (o FAILED)
  ▼
GET /knowledge-bases/{id}/documents/{doc_id}
  │  el cliente consulta el estado y progreso cuando quiere
  └─ retorna status + chunks_processed + chunks_total + progress_percentage
```

---

## Estados del documento

| Estado       | Descripción                                               |
|--------------|-----------------------------------------------------------|
| `PENDING`    | Documento recibido, en espera en la cola                  |
| `PROCESSING` | Worker tomó el job, extrayendo/embeddingando chunks       |
| `PROCESSED`  | Todos los chunks fueron embeddingados correctamente       |
| `FAILED`     | Error irrecuperable durante el procesamiento              |

---

## Campos de progreso (tabla `documents`)

```sql
chunks_total      INTEGER NOT NULL DEFAULT 0  -- total de chunks generados
chunks_processed  INTEGER NOT NULL DEFAULT 0  -- chunks ya embeddingados
```

`progress_percentage = (chunks_processed / chunks_total) * 100`

Mientras `chunks_total = 0` el progreso es indeterminado (extracción de texto en curso).

---

## Flujo detallado del worker

```python
async def process_document_job(document_id: UUID):
    # 1. Marcar como PROCESSING
    await document_repo.update_status(document_id, "PROCESSING")

    # 2. Extraer texto
    raw_text = extractor_service.extract(file_path, file_type)
    clean_text = text_cleaner.clean(raw_text)
    chunks = text_chunker.split_text(clean_text)

    # 3. Registrar total de chunks
    await document_repo.update_progress(
        document_id,
        chunks_processed=0,
        chunks_total=len(chunks)
    )

    # 4. Embeddings chunk por chunk con actualización de progreso
    for index, chunk_text in enumerate(chunks):
        chunk = await chunk_repo.create(...)
        embedding = await embedding_service.generate_embedding(chunk_text)
        await embedding_repo.create(chunk_id=chunk.id, embedding=embedding)

        await document_repo.update_progress(
            document_id,
            chunks_processed=index + 1
        )

    # 5. Marcar como PROCESSED
    await document_repo.update_status(document_id, "PROCESSED")
```

---

## Stack recomendado

### Opción A — Simple (sin infraestructura adicional)
- **ARQ** + **Redis**: worker async nativo Python, ideal para proyectos FastAPI
- Redis como broker y result backend
- Fácil de dockerizar

### Opción B — Enterprise
- **Celery** + **Redis/RabbitMQ**: más maduro, mejor ecosistema, retry y dead-letter queues
- Integra bien con monitoreo (Flower)

### Opción C — Cloud-native
- **AWS SQS** + **Lambda** o **ECS Workers**: sin servidor de cola que mantener
- Ideal si ya estás en AWS

---

## Implementación con ARQ (recomendado para este proyecto)

### 1. Instalar

```bash
pip install arq redis
```

### 2. Definir el worker

```python
# app/workers/document_worker.py
from arq import cron
from app.modules.documents.use_cases.process_document_use_case import ProcessDocumentUseCase

async def process_document(ctx, document_id: str, file_path: str, file_type: str):
    async with AsyncSessionLocal() as db:
        use_case = ProcessDocumentUseCase(db)
        await use_case.execute_from_job(document_id, file_path, file_type)

class WorkerSettings:
    functions = [process_document]
    redis_settings = RedisSettings(host="localhost", port=6379)
    max_jobs = 10
    job_timeout = 3600  # 1 hora máximo por job
    retry_jobs = True
    max_tries = 3
```

### 3. Encolar desde el controller

```python
# En lugar de procesar directo:
await redis.enqueue_job(
    "process_document",
    document_id=str(document.id),
    file_path=tmp_path,
    file_type=file_type
)
return document  # 202 Accepted, status=PENDING
```

### 4. Endpoint de estado

```
GET /knowledge-bases/{id}/documents/{doc_id}

{
  "id": "...",
  "status": "PROCESSING",
  "chunks_total": 142,
  "chunks_processed": 67,
  "progress_percentage": 47.2
}
```

---

## Consideraciones de escala

| Aspecto              | Sin cola (actual)          | Con cola (propuesto)         |
|----------------------|---------------------------|------------------------------|
| Timeout HTTP         | Posible en docs grandes   | Nunca (respuesta inmediata)  |
| Concurrencia         | Limitado por workers HTTP | N workers independientes     |
| Visibilidad          | Ninguna                   | Progreso en tiempo real      |
| Reintentos           | No                        | Sí (configurable)            |
| Prioridades          | No                        | Sí (colas de alta/baja prio) |
| Dead-letter queue    | No                        | Sí                           |
| Escalado horizontal  | Complejo                  | Agregar workers fácilmente   |

---

## Estado actual del código

La lógica de procesamiento ya está lista en `ProcessDocumentUseCase` con:

- Ciclo de estados `PENDING → PROCESSING → PROCESSED / FAILED`
- Actualización de `chunks_processed` después de cada chunk
- `chunks_total` registrado antes de empezar los embeddings

Lo que falta para tener la cola completa es:

- [ ] Instalar ARQ + Redis
- [ ] Crear `app/workers/document_worker.py`
- [ ] Modificar el controller para encolar en lugar de ejecutar directo
- [ ] Agregar `GET /knowledge-bases/{id}/documents/{doc_id}` (endpoint de estado)
- [ ] Levantar Redis en `docker-compose.yml`
- [ ] Agregar worker al `docker-compose.yml`
