import httpx

from app.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def chat(self, prompt: str) -> str | None:
        url = f"{str(self.settings.ollama_base_url).rstrip('/')}/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise, local-first personal assistant. Be practical and kind.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        return data.get("message", {}).get("content")

    async def embed(self, text: str) -> list[float] | None:
        """Return an embedding vector for *text*, or None if Ollama is unavailable."""
        url = f"{str(self.settings.ollama_base_url).rstrip('/')}/api/embed"
        payload = {"model": self.settings.ollama_model, "input": text}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        embeddings = data.get("embeddings")
        if embeddings and isinstance(embeddings, list) and len(embeddings) > 0:
            return embeddings[0]
        return None

