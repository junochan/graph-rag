"""
LLM abstraction layer with pluggable backends.
"""

from abc import ABC, abstractmethod
from typing import Generator

import httpx
from openai import AzureOpenAI, OpenAI

from src.config import get_settings


class LLMBase(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a chat completion."""
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming chat completion."""
        pass


class OpenAILLM(LLMBase):
    """OpenAI LLM implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.model = model
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens

        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["base_url"] = api_base

        self.client = OpenAI(**kwargs)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a chat completion."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming chat completion."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AzureOpenAILLM(LLMBase):
    """Azure OpenAI LLM implementation."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-02-15-preview",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.deployment = deployment
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens

        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a chat completion."""
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
        )
        return response.choices[0].message.content or ""

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming chat completion."""
        stream = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature or self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OllamaLLM(LLMBase):
    """Ollama LLM implementation."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a chat completion."""
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature or self.default_temperature,
                        "num_predict": max_tokens or self.default_max_tokens,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming chat completion."""
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature or self.default_temperature,
                        "num_predict": max_tokens or self.default_max_tokens,
                    },
                },
            ) as response:
                for line in response.iter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if content := data.get("message", {}).get("content"):
                            yield content


class CustomLLM(LLMBase):
    """Custom LLM endpoint implementation (OpenAI-compatible)."""

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a chat completion."""
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "messages": messages,
                    "temperature": temperature or self.default_temperature,
                    "max_tokens": max_tokens or self.default_max_tokens,
                    "stream": False,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Generate a streaming chat completion."""
        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{self.endpoint}/v1/chat/completions",
                json={
                    "messages": messages,
                    "temperature": temperature or self.default_temperature,
                    "max_tokens": max_tokens or self.default_max_tokens,
                    "stream": True,
                },
                headers=self._get_headers(),
            ) as response:
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        chunk = json.loads(data)
                        if content := chunk["choices"][0].get("delta", {}).get("content"):
                            yield content


def get_llm() -> LLMBase:
    """Factory function to get configured LLM instance."""
    settings = get_settings()
    llm_config = settings.llm

    if llm_config.type == "openai":
        return OpenAILLM(
            api_key=llm_config.openai_api_key,
            api_base=llm_config.openai_api_base,
            model=llm_config.openai_model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
    elif llm_config.type == "azure":
        if not all([llm_config.azure_api_key, llm_config.azure_endpoint, llm_config.azure_deployment]):
            raise ValueError("Azure API key, endpoint, and deployment are required")
        return AzureOpenAILLM(
            api_key=llm_config.azure_api_key,
            endpoint=llm_config.azure_endpoint,
            deployment=llm_config.azure_deployment,
            api_version=llm_config.azure_api_version,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
    elif llm_config.type == "ollama":
        return OllamaLLM(
            host=llm_config.ollama_host,
            model=llm_config.ollama_model,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
    elif llm_config.type == "custom":
        if not llm_config.custom_endpoint:
            raise ValueError("Custom LLM endpoint is required")
        return CustomLLM(
            endpoint=llm_config.custom_endpoint,
            api_key=llm_config.custom_api_key,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
        )
    else:
        raise ValueError(f"Unknown LLM type: {llm_config.type}")
