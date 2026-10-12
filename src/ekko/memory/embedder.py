"""CPU text embedding service encapsulating FastEmbed (bge-small-en-v1.5)."""

import asyncio

from fastembed import TextEmbedding

from ekko.logger import get_logger

logger = get_logger("ekko.memory.embedder")

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


class TextEmbedder:
    """Generates dense vector embeddings locally on CPU using FastEmbed ONNX runtime."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model: TextEmbedding | None = None

    def _get_model(self) -> TextEmbedding:
        """Lazily initialize FastEmbed model upon first invocation."""
        if self._model is None:
            logger.info("Initializing FastEmbed model: %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors synchronously, materializing generator in thread pool."""
        if not texts:
            return []
        model = self._get_model()
        return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in model.embed(texts)]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors for a list of strings."""
        return self._embed_batch_sync(texts)

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding vector for a single query string."""
        results = self.embed([query])
        return results[0] if results else [0.0] * EMBEDDING_DIM

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors asynchronously on a worker thread."""
        return await asyncio.to_thread(self._embed_batch_sync, texts)

    async def async_embed(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors asynchronously on a worker thread."""
        return await self.embed_batch(texts)

    async def async_embed_query(self, query: str) -> list[float]:
        """Generate embedding vector for a single query string asynchronously on a worker thread."""
        return await asyncio.to_thread(self.embed_query, query)
