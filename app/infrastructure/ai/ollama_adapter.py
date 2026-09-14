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
        return self._generate(prompt)

    def rephrase(self, text: str) -> str:
        prompt = (
            "Tu es un assistant pour une plateforme de communication scolaire.\n"
            "Reformule le message suivant en version diplomatique, polie et "
            "professionnelle, adaptee a la communication entre un enseignant ou "
            "une ecole et des parents. Conserve le sens original et la langue du "
            "message. Ne reponds qu'avec la version reformulee, sans commentaire.\n\n"
            f"{text}"
        )
        return self._generate(prompt)

    def _generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ServiceUnavailableError(
                "L'assistant IA est indisponible"
            ) from exc
        return (response.json().get("response") or "").strip()
