import logging
import json
from collections.abc import AsyncGenerator
import anthropic

from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SYSTEM_PROMPT
from backend.services.llm_provider import LLMProvider, T

logger = logging.getLogger("matchflix.anthropic")

class ClaudeProvider(LLMProvider):
    """LLM-provider die communiceert met de Anthropic (Claude) API."""

    def __init__(self, api_key: str = ANTHROPIC_API_KEY, model: str = CLAUDE_MODEL, system_prompt: str = SYSTEM_PROMPT):
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY ontbreekt. ClaudeProvider zal niet werken.")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

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
    ) -> T | dict:
        # Negeer het meegegeven model (bijv. Ollama-modelnaam) en gebruik altijd het Claude model
        model = self.model
        logger.info(f"Claude generate_json (model={model})")

        system = self.system_prompt
        if schema:
            system += f"\n\nBELANGRIJK: Je antwoord MOET voldoen aan dit JSON-schema:\n{json.dumps(schema.model_json_schema(), indent=2)}"
            system += "\nRetourneer UITSLUITEND de JSON-output."

        try:
            response = await self.client.messages.create(
                model=model or self.model,
                max_tokens=num_predict,
                temperature=temperature,
                system=system,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            # Basic JSON extraction if there's markdown fluff
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            if schema:
                return schema(**data)
            return data
        except Exception as e:
            logger.error(f"Fout bij Claude request: {e}")
            raise

    async def generate_json_stream(
        self,
        model: str,
        prompt: str,
        schema: type[T] | None = None,
        temperature: float = 0.1,
        num_predict: int = 2048,
        num_ctx: int = 8192,
        think: bool = False,
    ) -> AsyncGenerator[dict, None]:
        model = self.model
        system = self.system_prompt
        async with self.client.messages.stream(
            model=model,
            max_tokens=num_predict,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for event in stream:
                if event.type == "text":
                    yield {"type": "token", "data": event.text}
        
        # Result type event is handled at the end of the generator by the caller usually,
        # but here we just stream tokens.

    async def generate_embedding(self, text: str) -> list[float]:
        # Anthropic does not provide an embedding endpoint. 
        # We might need to use Ollama or another provider for this.
        logger.warning("ClaudeProvider biedt geen embeddings aan. Gebruik OllamaProvider voor embeddings.")
        return []

    async def check_status(self) -> dict:
        if not ANTHROPIC_API_KEY:
            return {"online": False, "error": "API Key ontbreekt"}
        return {"online": True, "model": self.model}
