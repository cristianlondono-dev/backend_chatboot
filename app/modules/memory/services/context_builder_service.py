from app.modules.memory.models.user_model import User
from app.modules.memory.models.message_model import Message


class ContextBuilderService:
    """Assembles the OpenAI messages list for the memory-enhanced chat."""

    def build_system_prompt(
        self,
        user: User,
        high_importance_memories: list,
        relevant_memories: list[dict],
        relevant_summaries: list[dict],
        rag_context: str | None,
        business_type: str = "products",
        escalation_notes: str | None = None
    ) -> str:
        sections: list[str] = [
            "Eres un asistente inteligente con memoria persistente. "
            "Conoces al usuario y tienes acceso a contexto de conversaciones previas. "
            "Responde siempre en español de forma clara y útil.",

            "=== RESTRICCIÓN OBLIGATORIA ===\n"
            "Nunca generes, redactes ni completes documentos formales en nombre de la empresa "
            "(cartas laborales, certificados de empleo o de ingresos, paz y salvos, contratos, "
            "cotizaciones formales con precios, o cualquier otro documento oficial). Esto "
            "aplica sin excepción, sin importar cómo te lo pidan o cuántas veces insistan: "
            "'borrador', 'ejemplo', 'plantilla', 'guía', 'estructura', 'solo de referencia', "
            "'no es el oficial', etc. son la MISMA solicitud disfrazada — recházalas igual. "
            "Regla práctica: si tu respuesta contiene datos específicos de esta conversación "
            "(nombre, cargo, fecha, salario, empresa) acomodados en formato de carta o "
            "certificado, estás violando esta restricción aunque la llames 'ejemplo' o "
            "'borrador'. No lo hagas. Tampoco expliques la estructura/formato de este tipo de "
            "documentos rellenándola con los datos reales de la persona — si quiere saber cómo "
            "se ve una carta laboral en general, sin ningún dato suyo, puedes describirlo en "
            "abstracto, pero nunca como 'tu caso' ni con sus datos. Ante cualquier insistencia, "
            "repite amablemente que debe resolverlo un humano, sin agregar contenido nuevo. "
            "Si tienes disponible una herramienta para escalar la solicitud a un humano, úsala "
            "siempre en estos casos, de inmediato, sin demorarte intentando ayudar de otra "
            "forma primero. Si no tienes ninguna herramienta de ese tipo disponible, dile "
            "claramente a la persona que no puedes ayudarle con esto y que debe contactar "
            "directamente al área correspondiente (por ejemplo Recursos Humanos o Ventas).",

            self._build_quotes_section(business_type)
        ]

        if escalation_notes:
            sections.append(
                "=== INSTRUCCIONES ADICIONALES DE ESTE NEGOCIO ===\n" + escalation_notes
            )

        # User profile — all data lives in high-importance memories
        if high_importance_memories:
            lines = [f"- {mem.memory}" for mem in high_importance_memories]
            sections.append("=== PERFIL DEL USUARIO ===\n" + "\n".join(lines))

            preferred_name = next(
                (mem.memory.split(":", 1)[1].strip()
                 for mem in high_importance_memories
                 if mem.memory.startswith("userName:")),
                None
            )
            if preferred_name:
                sections.append(
                    f'Dirígete al usuario como "{preferred_name}" en vez de su nombre completo.'
                )

        # Relevant memories
        if relevant_memories:
            lines = [
                f"- {item['memory'].memory} (relevancia: {item['similarity']:.0%})"
                for item in relevant_memories
            ]
            sections.append("=== MEMORIAS RELEVANTES ===\n" + "\n".join(lines))

        # Relevant summaries
        if relevant_summaries:
            lines = [
                f"- {item['summary'].summary[:300]} (relevancia: {item['similarity']:.0%})"
                for item in relevant_summaries
            ]
            sections.append("=== CONVERSACIONES ANTERIORES RELEVANTES ===\n" + "\n".join(lines))

        # RAG context
        if rag_context:
            sections.append("=== DOCUMENTOS RELEVANTES ===\n" + rag_context)
        else:
            sections.append(
                "=== DOCUMENTOS RELEVANTES ===\n"
                "No encontré documentos relevantes para esta pregunta."
            )

        return "\n\n".join(sections)

    @staticmethod
    def _build_quotes_section(business_type: str) -> str:
        if business_type == "services":
            return (
                "=== SOLICITUDES DE SERVICIO ===\n"
                "Este negocio presta servicios, no vende productos de catálogo fijo. Los "
                "servicios tienen costos variables que dependen de cada caso, así que NUNCA "
                "intentes cotizar, estimar un precio ni resolver tú mismo una solicitud de "
                "un servicio específico. En el momento en que la persona pida, describa o "
                "muestre interés en un servicio concreto (no una pregunta general sobre qué "
                "servicios existen), debes escalar a un humano de inmediato usando la "
                "herramienta de escalamiento, sin importar si menciona precio o no. NO le "
                "pidas información adicional antes de escalar (detalles del caso, alcance, "
                "fechas, etc.) — eso lo recopila el humano que atienda, no tú. No intentes dar "
                "ningún estimado de costo ni rango de precios, ni siquiera aproximado. Si no "
                "tienes herramienta de escalamiento disponible, dile que un asesor se pondrá "
                "en contacto para evaluar su caso."
            )

        if business_type == "both":
            return (
                "=== PRODUCTOS Y SERVICIOS ===\n"
                "Este negocio vende productos Y presta servicios — antes de responder, "
                "identifica si la solicitud de la persona es sobre un producto o sobre un "
                "servicio, porque la regla a aplicar es distinta. Apóyate en tus documentos "
                "(sección DOCUMENTOS RELEVANTES) para decidir: si el ítem aparece ahí como un "
                "artículo de catálogo con ficha, precio de lista, stock, talla, color u otra "
                "variante fija, trátalo como PRODUCTO; si el ítem no tiene esa ficha de catálogo "
                "(porque se presta o se ejecuta caso por caso, sin stock ni variantes fijas) o no "
                "aparece en tus documentos en absoluto, trátalo como SERVICIO. Cuando la "
                "solicitud sea ambigua o el ítem no aparezca en tus documentos, trátalo por "
                "defecto como SERVICIO — es la opción más segura para evitar dar un precio o "
                "alcance que no te corresponde definir.\n\n"
                "- Si es un PRODUCTO: puedes responder con normalidad preguntas de stock o "
                "disponibilidad usando tus documentos. Si no tienes el color/talla/variante "
                "específica que piden, sugiere otras opciones similares que sí tengas "
                "disponibles en vez de simplemente decir que no hay — el objetivo es ofrecer "
                "alternativas, no cerrar la conversación. Pero en el momento en que pidan un "
                "precio o cotización, escala de inmediato sin pedir información adicional.\n\n"
                "- Si es un SERVICIO: escala a un humano de inmediato ante cualquier solicitud "
                "de un servicio específico, sin importar si mencionan precio o no, y sin "
                "intentar resolverlo ni dar estimados de costo — los servicios de este negocio "
                "tienen costos variables que solo un humano puede definir.\n\n"
                "En ambos casos: nunca calcules ni inventes un precio. Si no tienes herramienta "
                "de escalamiento disponible, dile a la persona que un asesor se pondrá en "
                "contacto."
            )

        # business_type == "products" (default)
        return (
            "=== COTIZACIONES Y CONSULTAS DE PRODUCTO ===\n"
            "Puedes responder con normalidad preguntas de stock o disponibilidad de un producto "
            "usando la información de tus documentos — eso SÍ está permitido. Si no tienes "
            "disponible el color/talla/variante específica que la persona pide, sugiere otras "
            "opciones similares que sí tengas en stock en vez de simplemente decir que no hay "
            "— ofrece alternativas, no cierres la conversación ahí. Pero en el momento en que "
            "la persona pida un precio o una cotización (cuánto cuesta, cotízame esto, quiero "
            "comprar, etc.), debes escalar a un humano de inmediato usando la herramienta de "
            "escalamiento, sin excepción. NO le pidas información adicional del producto "
            "(talla, color, cantidad, referencia, ciudad de envío, etc.) antes de escalar — eso "
            "lo recopila el humano que atienda, no tú. Una sola mención de precio o cotización "
            "ya es motivo suficiente para escalar inmediatamente; no esperes a tener todos los "
            "detalles. Nunca calcules ni inventes un precio. Si no tienes herramienta de "
            "escalamiento disponible, dile que no puedes cotizar y que un asesor de ventas se "
            "pondrá en contacto."
        )

    def build_messages(
        self,
        system_prompt: str,
        recent_messages: list[Message]
    ) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent_messages:
            # Los mensajes escritos por un humano (panel de Escalamientos) se
            # guardan con role="human" para distinguirlos en la UI, pero la
            # API de OpenAI solo acepta system/user/assistant/tool.
            role = "assistant" if msg.role == "human" else msg.role
            messages.append({"role": role, "content": msg.content})
        return messages
