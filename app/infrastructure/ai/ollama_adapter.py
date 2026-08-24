import requests

from app.domain.errors import ServiceUnavailableError
from app.domain.ports.services import TextAssistantPort


class OllamaTextAssistant(TextAssistantPort):
    def __init__(
        self, base_url: str, model: str, timeout: int = 45
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def summarize(self, texts: list[str]) -> str:
        conversation = "\n".join(f"- {text}" for text in texts)
        prompt = (
            "Tu es un assistant pour une plateforme de communication scolaire.\n"
            "Resume en francais les messages de conversation suivants en quelques "
            "points cles, de fagon neutre et concise. Ne reponds qu'avec le resume.\n\n"
            f"{conversation}"
        )
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ServiceUnavailableError(
                "AI assistant is unavailable"
            ) from exc
        return (response.json().get("response") or "").strip()
