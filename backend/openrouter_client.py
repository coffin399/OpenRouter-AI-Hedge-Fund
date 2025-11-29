import os
from typing import Any, Dict, List, Optional

import httpx


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://openrouter.ai/api/v1") -> None:
        self.base_url = base_url
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_TITLE", "OpenRouter AI Hedge Fund"),
        }

    async def chat(self, model: str, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": model, "messages": messages}
        payload.update(kwargs)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.post("/chat/completions", json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def list_models(self, free_only: bool = False) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            response = await client.get("/models", headers=self._headers())
            response.raise_for_status()
            data = response.json()
        models: List[Dict[str, Any]] = data.get("data", [])
        if not free_only:
            return models
        free_models: List[Dict[str, Any]] = []
        for model in models:
            pricing = model.get("pricing") or {}
            prompt_price = pricing.get("prompt")
            completion_price = pricing.get("completion")
            is_free = (prompt_price == 0 or prompt_price is None) and (completion_price == 0 or completion_price is None)
            if is_free:
                free_models.append(model)
        return free_models

    async def is_free_model(self, model_id: str) -> bool:
        models = await self.list_models(free_only=True)
        for model in models:
            if model.get("id") == model_id:
                return True
        return False
