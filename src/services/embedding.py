"""
Embedding model abstraction layer with pluggable backends.
"""

from abc import ABC, abstractmethod

import httpx
from openai import OpenAI

from src.config import get_settings


class EmbeddingModelBase(ABC):
    """Abstract base class for embedding models."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class OpenAIEmbedding(EmbeddingModelBase):
    """OpenAI embedding model implementation."""

    # Known dimensions for embedding models
    MODEL_DIMENSIONS = {
        # OpenAI models
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        # Aliyun/DashScope models
        "text-embedding-v1": 1536,
        "text-embedding-v2": 1536,
        "text-embedding-v3": 1024,
        "text-embedding-v4": 1024,
    }

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "text-embedding-3-small",
    ):
        self.model = model
        self._dimension = self.MODEL_DIMENSIONS.get(model, 1536)

        # Initialize OpenAI client
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["base_url"] = api_base

        self.client = OpenAI(**kwargs)

    def embed(self, texts: list[str], batch_size: int = 10) -> list[list[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Maximum batch size (some APIs like Aliyun limit to 10)
        """
        if not texts:
            return []

        all_embeddings = []
        
        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension


class CustomEmbedding(EmbeddingModelBase):
    """Custom embedding endpoint implementation."""

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        dimension: int = 1536,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.endpoint,
                json={"texts": texts},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("embeddings", [])

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension


def get_embedding_model() -> EmbeddingModelBase:
    """Factory function to get configured embedding model."""
    settings = get_settings()
    emb_config = settings.embedding

    if emb_config.type == "openai":
        return OpenAIEmbedding(
            api_key=emb_config.openai_api_key,
            api_base=emb_config.openai_api_base,
            model=emb_config.openai_model,
        )
    elif emb_config.type == "huggingface":
        # TODO: Implement HuggingFace embedding
        raise NotImplementedError("HuggingFace embedding not implemented yet")
    elif emb_config.type == "custom":
        if not emb_config.custom_endpoint:
            raise ValueError("Custom embedding endpoint is required")
        return CustomEmbedding(
            endpoint=emb_config.custom_endpoint,
            api_key=emb_config.custom_api_key,
            dimension=settings.vector_store.dimension,
        )
    else:
        raise ValueError(f"Unknown embedding type: {emb_config.type}")
