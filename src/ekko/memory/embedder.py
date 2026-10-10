"""CPU text embedding service encapsulating FastEmbed (bge-small-en-v1.5)."""

from typing import Any
from ekko.utils.logger import get_logger

logger = get_logger("ekko.memory.embedder")

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


class TextEmbedder:
    """Generates dense vector embeddings locally on CPU using FastEmbed ONNX runtime."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazily initialize FastEmbed model upon first invocation."""
        if self._model is None:
            logger.info("Initializing FastEmbed model: %s", self.model_name)
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors for a list of strings."""
        if not texts:
            return []
        model = self._get_model()
        embeddings_iter = model.embed(texts)
        return [list(vec.tolist() if hasattr(vec, "tolist") else vec) for vec in embeddings_iter]

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding vector for a single query string."""
        results = self.embed([query])
        return results[0] if results else [0.0] * EMBEDDING_DIM
