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
