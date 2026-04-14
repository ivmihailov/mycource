import json
from dataclasses import dataclass
from urllib import error, request

from django.conf import settings

from apps.ai_support.exceptions import AIProviderError, AIUnavailableError


@dataclass
class AICompletionResult:
    model_id: str
    content: str
    raw_response: dict


class AIProvider:
    def list_models(self):
        raise NotImplementedError

    def chat(
        self,
        *,
        model_id,
        messages,
        response_format=None,
        temperature=0.2,
        max_tokens=None,
        require_parameters=False,
    ):
        raise NotImplementedError


class OpenRouterProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL.rstrip("/")
        self.http_referer = settings.OPENROUTER_HTTP_REFERER
        self.app_title = settings.OPENROUTER_APP_TITLE
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

    def _ensure_configured(self):
        if not settings.AI_ENABLED:
            raise AIUnavailableError("AI-функции отключены в настройках.")
        if not self.api_key:
            raise AIUnavailableError("OPENROUTER_API_KEY не задан.")

    def _headers(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.http_referer:
            referer = self._safe_header_value(self.http_referer)
            if referer:
                headers["HTTP-Referer"] = referer
        if self.app_title:
            title = self._safe_header_value(self.app_title) or "MyCourse"
            headers["X-Title"] = title
        return headers

    @staticmethod
    def _safe_header_value(value):
        try:
            return str(value).encode("latin-1", errors="strict").decode("latin-1")
        except UnicodeEncodeError:
            return None

    def _request(self, method, path, payload=None):
        self._ensure_configured()
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(),
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.load(response)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise AIProviderError(f"OpenRouter HTTP {exc.code}: {body[:500]}") from exc
        except error.URLError as exc:
            raise AIProviderError(f"Не удалось подключиться к OpenRouter: {exc.reason}") from exc
        except TimeoutError as exc:
            raise AIProviderError("Истек таймаут запроса к OpenRouter.") from exc

    def list_models(self):
        payload = self._request("GET", "/models")
        return payload.get("data", [])

    def chat(
        self,
        *,
        model_id,
        messages,
        response_format=None,
        temperature=0.2,
        max_tokens=None,
        require_parameters=False,
    ):
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format
        if require_parameters:
            payload["provider"] = {"require_parameters": True}

        response_payload = self._request("POST", "/chat/completions", payload)
        try:
            choice = response_payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("OpenRouter вернул неожиданный формат ответа.") from exc

        content = choice.get("content", "")
        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        if not isinstance(content, str):
            content = str(content)

        return AICompletionResult(
            model_id=response_payload.get("model") or model_id,
            content=content.strip(),
            raw_response=response_payload,
        )
