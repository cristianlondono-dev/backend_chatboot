from app.modules.llm.services.openai_chat_service import OpenAIChatService


class OnboardingService:
    """
    Generates natural, warm onboarding messages using the LLM.
    Replaces raw question text with conversational responses.
    """

    def __init__(self):
        self.chat_service = OpenAIChatService()

    def greeting_with_question(self, user_first_message: str, question: str) -> str:
        """First contact: warm greeting + first onboarding question naturally embedded."""
        prompt = f"""Eres un asistente virtual amigable. El usuario inició la conversación con:
"{user_first_message}"

Genera una bienvenida cálida y natural en español que:
1. Salude cordialmente al usuario
2. Indique que con gusto le ayudarás
3. Haga esta pregunta de forma fluida: "{question}"

Máximo 2 oraciones. Sin asteriscos, sin markdown, sin emojis excesivos."""
        return self.chat_service.generate_response(prompt)

    def transition_with_question(self, user_answer: str, next_question: str) -> str:
        """Intermediate step: acknowledge the previous answer + ask the next question."""
        prompt = f"""Eres un asistente virtual amigable respondiendo en español.
El usuario respondió: "{user_answer}"
Ahora debes preguntarle: "{next_question}"

Genera 1-2 oraciones que acusen recibo de forma natural y hagan la siguiente pregunta fluidamente.
Sin asteriscos, sin markdown."""
        return self.chat_service.generate_response(prompt)

    def nickname_greeting(self, user_first_message: str, full_name: str) -> str:
        """First contact, compound first name: warm greeting asking how to address them."""
        prompt = f"""Eres un asistente virtual amigable. El usuario se llama "{full_name}" y escribió:
"{user_first_message}"

Genera un saludo cálido y natural en español que:
1. Salude a la persona por su nombre completo ("{full_name}")
2. Le pregunte cómo prefiere que la llamen, ofreciendo como opciones cada palabra de su nombre
   por separado y el nombre completo (ej. si se llama "Cristian Camilo", las opciones son
   Cristian, Camilo o Cristian Camilo)

Máximo 2 oraciones. Sin asteriscos, sin markdown, sin emojis excesivos."""
        return self.chat_service.generate_response(prompt)

    def extract_nickname(self, full_name: str, user_answer: str) -> str:
        """
        Pulls just the chosen name/nickname out of a free-text reply to the
        nickname question — the reply often carries extra text (a follow-up
        question asked in the same message), which must not end up in memory.
        """
        name_hint = f'El nombre completo de la persona es "{full_name}". ' if full_name else ""
        prompt = f"""{name_hint}Le preguntamos cómo prefiere que la llamemos y respondió:
"{user_answer}"

Responde ÚNICAMENTE con el nombre o apodo que eligió — sin comillas, sin puntuación,
sin explicaciones, sin texto adicional aunque la respuesta contenga otras cosas."""
        nickname = self.chat_service.generate_response(prompt).strip().strip('."\' ')

        if not nickname or len(nickname) > 40 or "\n" in nickname:
            fallback_source = full_name or user_answer
            nickname = fallback_source.strip().split()[0] if fallback_source.strip() else user_answer.strip()

        return nickname

    def extract_answers(self, remaining_questions: list[dict], user_message: str) -> dict[str, str]:
        """
        Given the onboarding questions still pending and a free-text user
        message, asks the LLM which of those questions the message already
        answers — even questions that haven't been asked yet (e.g. the user
        volunteers their name and the service they need in the same sentence).

        Returns {label: extracted_value} only for questions the model could
        identify with confidence; never invents values for data the message
        doesn't contain. Best-effort: any failure (LLM error, malformed JSON,
        unexpected shape) is swallowed and returns {} so onboarding falls
        back to asking the questions one by one, exactly like before this
        feature existed.
        """
        if not remaining_questions:
            return {}

        labeled_questions = [
            {"label": self.extract_memory_label(q), "question": q["question"]}
            for q in remaining_questions
        ]
        questions_block = "\n".join(
            f'- Etiqueta "{lq["label"]}": {lq["question"]}' for lq in labeled_questions
        )
        valid_labels = ", ".join(f'"{lq["label"]}"' for lq in labeled_questions)

        prompt = f"""Estas son las preguntas de onboarding pendientes, cada una con su etiqueta:
{questions_block}

El usuario escribió este mensaje:
"{user_message}"

Identifica cuáles de esas preguntas ya quedaron respondidas dentro de ese mensaje,
aunque no se le haya hecho la pregunta directamente. Responde ÚNICAMENTE con un
objeto JSON cuyas claves sean EXACTAMENTE las etiquetas indicadas arriba ({valid_labels})
y cuyos valores sean el dato extraído del mensaje para esa pregunta.

Reglas estrictas:
- Incluye SOLO las etiquetas cuya respuesta esté realmente presente en el mensaje.
- Si una pregunta no fue respondida en el mensaje, NO incluyas su etiqueta en el JSON.
- Nunca inventes ni infieras un valor que no esté explícito o claramente implícito en el mensaje.
- No agregues etiquetas distintas a las indicadas.
- Si ninguna pregunta fue respondida, responde con un objeto JSON vacío: {{}}"""

        try:
            result = self.chat_service.generate_json(prompt)
        except Exception:
            return {}

        if not isinstance(result, dict):
            return {}

        valid = {lq["label"] for lq in labeled_questions}
        return {
            label: str(value).strip()
            for label, value in result.items()
            if label in valid and str(value).strip()
        }

    def completion_message(self) -> str:
        """Onboarding complete: warm message confirming readiness to help."""
        prompt = """Genera un mensaje corto y amigable en español (1-2 oraciones) que indique
que ya tienes la información necesaria y que estás listo para ayudar.
Sin asteriscos, sin markdown."""
        return self.chat_service.generate_response(prompt)

    @staticmethod
    def extract_memory_label(question_dict: dict) -> str:
        """
        Extracts the memory label from an onboarding question dict.
        Works with any key name ('memory_key', 'service_key', etc.) —
        returns the value of the first key that is not 'question'.
        """
        return next(
            (v for k, v in question_dict.items() if k != "question"),
            "Información"
        )
