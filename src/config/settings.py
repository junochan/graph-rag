"""
Configuration management using pydantic-settings.
Supports environment variables and .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NebulaGraphConfig(BaseModel):
    """NebulaGraph database configuration."""

    hosts: list[str] = Field(default=["127.0.0.1:9669"], description="NebulaGraph hosts")
    username: str = Field(default="root", description="Username")
    password: str = Field(default="nebula", description="Password")
    space: str = Field(default="graph_rag", description="Graph space name")
    max_connection_pool_size: int = Field(default=10, description="Max connection pool size")


class VectorStoreConfig(BaseModel):
    """Vector store configuration."""

    type: Literal["qdrant", "milvus", "chroma", "faiss"] = Field(
        default="qdrant", description="Vector store type"
    )
    # Qdrant specific
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_api_key: str | None = Field(default=None, description="Qdrant API key")
    qdrant_collection: str = Field(default="graph_rag", description="Qdrant collection name")
    # Milvus specific
    milvus_host: str = Field(default="localhost", description="Milvus host")
    milvus_port: int = Field(default=19530, description="Milvus port")
    milvus_collection: str = Field(default="graph_rag", description="Milvus collection name")
    # Chroma specific
    chroma_host: str = Field(default="localhost", description="Chroma host")
    chroma_port: int = Field(default=8000, description="Chroma port")
    chroma_collection: str = Field(default="graph_rag", description="Chroma collection name")
    # FAISS specific
    faiss_index_path: str = Field(default="./data/faiss_index", description="FAISS index path")
    # Common
    dimension: int = Field(default=1536, description="Vector dimension")


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    type: Literal["openai", "huggingface", "custom"] = Field(
        default="openai", description="Embedding model type"
    )
    # OpenAI specific
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_api_base: str | None = Field(default=None, description="OpenAI API base URL")
    openai_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")
    # HuggingFace specific
    huggingface_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model name",
    )
    # Custom endpoint
    custom_endpoint: str | None = Field(default=None, description="Custom embedding endpoint")
    custom_api_key: str | None = Field(default=None, description="Custom embedding API key")


class LLMConfig(BaseModel):
    """LLM configuration."""

    type: Literal["openai", "azure", "ollama", "custom"] = Field(
        default="openai", description="LLM type"
    )
    # OpenAI specific
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_api_base: str | None = Field(default=None, description="OpenAI API base URL")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")
    # Azure specific
    azure_endpoint: str | None = Field(default=None, description="Azure endpoint")
    azure_api_key: str | None = Field(default=None, description="Azure API key")
    azure_deployment: str | None = Field(default=None, description="Azure deployment name")
    azure_api_version: str = Field(default="2024-02-15-preview", description="Azure API version")
    # Ollama specific
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama host")
    ollama_model: str = Field(default="llama3.2", description="Ollama model")
    # Custom endpoint
    custom_endpoint: str | None = Field(default=None, description="Custom LLM endpoint")
    custom_api_key: str | None = Field(default=None, description="Custom LLM API key")
    # Common
    temperature: float = Field(default=0.7, description="Temperature")
    max_tokens: int = Field(default=2048, description="Max tokens")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="Graph RAG", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=5000, description="Server port")

    # Sub-configurations
    nebula: NebulaGraphConfig = Field(default_factory=NebulaGraphConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
