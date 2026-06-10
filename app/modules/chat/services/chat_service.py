class ChatService:

    async def process_message(self, message: str) -> str:
        return f"Recibí tu mensaje: {message}"