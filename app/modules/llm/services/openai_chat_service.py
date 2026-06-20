import json
from dataclasses import dataclass, field
from collections.abc import AsyncGenerator

from openai import OpenAI, AsyncOpenAI

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


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResult:
    """
    Structured response from generate_with_tools().

    Either content or tool_calls will be set, never both at the same time.
    When the model wants to invoke a function, tool_calls is populated and
    content is None. The caller is responsible for executing the tools and
    continuing the conversation.
    """
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Raw assistant message dict — must be appended to messages before sending tool results
    raw_message: dict = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class OpenAIChatService:

    def __init__(self, api_key: str | None = None):
        key = api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=key)
        self.async_client = AsyncOpenAI(api_key=key)

    # ── Existing methods (unchanged signatures) ───────────────────────────────

    def generate_response_with_messages(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(model=_MODEL, messages=messages)
        except Exception as exc:
            error_logger.error(f"OpenAI chat error: {type(exc).__name__}: {exc}", exc_info=True)
            raise

        usage = response.usage
        cost = _chat_cost(_MODEL, usage.prompt_tokens, usage.completion_tokens)
        openai_logger.info(
            f"[chat-memory] model={_MODEL} | input={usage.prompt_tokens} | output={usage.completion_tokens} "
            f"| total={usage.total_tokens} | cost=${cost:.6f}"
        )
        return response.choices[0].message.content

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
        cost = _chat_cost(_MODEL, usage.prompt_tokens, usage.completion_tokens)
        openai_logger.info(
            f"[chat] model={_MODEL} | input={usage.prompt_tokens} | output={usage.completion_tokens} "
            f"| total={usage.total_tokens} | cost=${cost:.6f}"
        )
        return response.choices[0].message.content

    def generate_json(self, prompt: str) -> dict:
        """
        Same as generate_response() but requests JSON mode from the model and
        parses the result. Extraction is a "nice to have" — malformed/empty
        output returns {} instead of raising, so callers can degrade
        gracefully. API/network errors still propagate, same as the other
        methods here; swallowing those to keep a flow alive is a decision for
        the caller (see OnboardingService.extract_answers).
        """
        try:
            response = self.client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
        except Exception as exc:
            error_logger.error(
                f"OpenAI chat error: {type(exc).__name__}: {exc}",
                exc_info=True
            )
            raise

        usage = response.usage
        cost = _chat_cost(_MODEL, usage.prompt_tokens, usage.completion_tokens)
        openai_logger.info(
            f"[chat-json] model={_MODEL} | input={usage.prompt_tokens} | output={usage.completion_tokens} "
            f"| total={usage.total_tokens} | cost=${cost:.6f}"
        )

        content = response.choices[0].message.content
        try:
            parsed = json.loads(content) if content else {}
        except (json.JSONDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

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
            if chunk.usage is not None:
                usage = chunk.usage
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

        if usage is not None:
            cost = _chat_cost(_MODEL, usage.prompt_tokens, usage.completion_tokens)
            openai_logger.info(
                f"[chat-stream] model={_MODEL} | input={usage.prompt_tokens} | output={usage.completion_tokens} "
                f"| total={usage.total_tokens} | cost=${cost:.6f}"
            )

    # ── New method: supports OpenAI function/tool calling ─────────────────────

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None
    ) -> ChatResult:
        """
        Call the model with optional tool definitions.

        When tools is None or empty the model responds normally and ChatResult.content
        contains the text (same behaviour as generate_response_with_messages).

        When the model decides to invoke a tool, ChatResult.tool_calls is populated
        and ChatResult.content is None. The caller must:
          1. Execute each tool call.
          2. Append ChatResult.raw_message to messages.
          3. Append one tool-result message per call.
          4. Call generate_with_tools() again until has_tool_calls is False.
        """
        kwargs: dict = {"model": _MODEL, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            error_logger.error(f"OpenAI chat error: {type(exc).__name__}: {exc}", exc_info=True)
            raise

        usage = response.usage
        cost = _chat_cost(_MODEL, usage.prompt_tokens, usage.completion_tokens)
        openai_logger.info(
            f"[chat-tools] model={_MODEL} | input={usage.prompt_tokens} | output={usage.completion_tokens} "
            f"| total={usage.total_tokens} | cost=${cost:.6f}"
        )

        choice = response.choices[0]
        msg = choice.message

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in msg.tool_calls
            ]
            raw_message = {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
            return ChatResult(tool_calls=tool_calls, raw_message=raw_message)

        return ChatResult(content=msg.content, raw_message={"role": "assistant", "content": msg.content})
