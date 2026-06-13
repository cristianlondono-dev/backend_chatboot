import json

from app.modules.llm.services.openai_chat_service import OpenAIChatService
from app.core.logging.loggers import application_logger, error_logger

_EXTRACTION_PROMPT = """Analiza el siguiente mensaje de usuario e identifica hechos importantes sobre él.
Solo extrae hechos objetivos que el usuario mencione explícitamente.
Devuelve una lista JSON. Si no hay hechos relevantes, devuelve [].

Formato de cada elemento:
{{"memory": "hecho en español", "importance": "high|medium|low"}}

Criterios de importancia:
- high: nombre, cargo, información personal clave
- medium: preferencias, relaciones, contexto laboral
- low: datos menores o circunstanciales

Ejemplos:
Mensaje: "Mi nombre es Ricardo y trabajo como supervisor nocturno"
Respuesta: [{{"memory": "Nombre: Ricardo", "importance": "high"}}, {{"memory": "Trabaja como supervisor nocturno", "importance": "high"}}]

Mensaje: "Hola, necesito información sobre vacaciones"
Respuesta: []

Mensaje: "{message}"
Respuesta:"""


class MemoryExtractionService:

    def __init__(self):
        self.chat_service = OpenAIChatService()

    def extract(self, user_message: str) -> list[dict]:
        prompt = _EXTRACTION_PROMPT.format(message=user_message.replace('"', "'"))
        try:
            raw = self.chat_service.generate_response(prompt)
            facts = json.loads(raw.strip())
            if isinstance(facts, list):
                return [f for f in facts if isinstance(f, dict) and "memory" in f and "importance" in f]
            return []
        except (json.JSONDecodeError, Exception) as exc:
            error_logger.warning(f"Memory extraction failed: {exc}")
            return []
