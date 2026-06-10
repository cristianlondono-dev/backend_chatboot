from openai import OpenAI, AsyncOpenAI
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.core.logging.loggers import openai_logger, error_logger

_MODEL = "gpt-4.1-mini"

# Cost per 1 million tokens (USD) — update if OpenAI changes pricing
_INPUT_COST_PER_M: dict[str, float] = {
    "gpt-4.1-mini": 0.40,
    "gpt-4o-mini": 0.15,
    "gpt-4o": 2.50,
}
_OUTPUT_COST_PER_M: dict[str, float] = {
    "gpt-4.1-mini": 1.60,
    "gpt-4o-mini": 0.60,
    "gpt-4o": 10.00,
}


def _chat_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    inp = _INPUT_COST_PER_M.get(model, 0.0) * input_tokens / 1_000_000
    out = _OUTPUT_COST_PER_M.get(model, 0.0) * output_tokens / 1_000_000
    return inp + out


class OpenAIChatService:

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_response(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
        except Exception as exc:
            error_logger.error(
                f"OpenAI chat error: {type(exc).__name__}: {exc}",
                exc_info=True
            )
            raise

        usage = response.usage
        input_t = usage.prompt_tokens
        output_t = usage.completion_tokens
        total_t = usage.total_tokens
        cost = _chat_cost(_MODEL, input_t, output_t)

        openai_logger.info(
            f"[chat] model={_MODEL} | input={input_t} | output={output_t} "
            f"| total={total_t} | cost=${cost:.6f}"
        )

        return response.choices[0].message.content

    async def generate_response_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            stream = await self.async_client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                stream_options={"include_usage": True}
            )
        except Exception as exc:
            error_logger.error(
                f"OpenAI chat stream error: {type(exc).__name__}: {exc}",
                exc_info=True
            )
            raise

        usage = None
        async for chunk in stream:
            # The final chunk from stream_options carries usage but no content
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        if usage is not None:
            input_t = usage.prompt_tokens
            output_t = usage.completion_tokens
            total_t = usage.total_tokens
            cost = _chat_cost(_MODEL, input_t, output_t)
            openai_logger.info(
                f"[chat-stream] model={_MODEL} | input={input_t} | output={output_t} "
                f"| total={total_t} | cost=${cost:.6f}"
            )
