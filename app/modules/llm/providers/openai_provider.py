from openai import OpenAI

from app.core.config import settings
from app.core.logging.loggers import openai_logger, error_logger

_embedding_cache: dict[str, list[float]] = {}
_EMBEDDING_CACHE_MAXSIZE = 512

# Cost per 1 million tokens (USD) — update if OpenAI changes pricing
_EMBEDDING_COST_PER_M: dict[str, float] = {
    "text-embedding-3-small": 0.020,
    "text-embedding-3-large": 0.130,
    "text-embedding-ada-002": 0.100,
}

_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingService:

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_embedding(self, text: str) -> list[float]:
        if text in _embedding_cache:
            openai_logger.info(
                f"[embedding] model={_EMBEDDING_MODEL} | tokens=0 | cost=$0.000000 | cached=True"
            )
            return _embedding_cache[text]

        try:
            response = self.client.embeddings.create(
                model=_EMBEDDING_MODEL,
                input=text
            )
        except Exception as exc:
            error_logger.error(
                f"OpenAI embedding error: {type(exc).__name__}: {exc}",
                exc_info=True
            )
            raise

        embedding = response.data[0].embedding

        tokens = response.usage.total_tokens
        cost_per_m = _EMBEDDING_COST_PER_M.get(_EMBEDDING_MODEL, 0.0)
        cost = tokens * cost_per_m / 1_000_000

        openai_logger.info(
            f"[embedding] model={_EMBEDDING_MODEL} | tokens={tokens} | cost=${cost:.6f} | cached=False"
        )

        if len(_embedding_cache) < _EMBEDDING_CACHE_MAXSIZE:
            _embedding_cache[text] = embedding

        return embedding
