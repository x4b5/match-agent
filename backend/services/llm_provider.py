import typing
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pydantic import BaseModel

T = typing.TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    """Abstracte basis voor LLM-providers (Ollama, OpenAI, etc.)."""

    @abstractmethod
    async def generate_json(
        self,
        model: str,
        prompt: str,
        schema: type[T] | None = None,
        temperature: float = 0.1,
        num_predict: int = 2048,
        num_ctx: int = 8192,
        think: bool = False,
        max_retries: int = 2,
    ) -> T | dict: ...

    @abstractmethod
    async def generate_json_stream(
        self,
        model: str,
        prompt: str,
        schema: type[T] | None = None,
        temperature: float = 0.1,
        num_predict: int = 2048,
        num_ctx: int = 8192,
        think: bool = False,
    ) -> AsyncGenerator[dict, None]: ...

    @abstractmethod
    async def generate_embedding(self, text: str) -> list[float]: ...

    @abstractmethod
    async def check_status(self) -> dict: ...
