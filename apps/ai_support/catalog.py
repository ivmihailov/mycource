from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from apps.ai_support.models import AIModelOption
from apps.ai_support.providers import OpenRouterProvider


CATALOG_CACHE_KEY = "ai_support:selected_models"


@dataclass
class CandidateModel:
    raw: dict
    model_id: str
    name: str
    context_length: int
    supports_structured_output: bool
    total_price: Decimal
    provider_name: str = "openrouter"


def _decimal_or_zero(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


class ModelCatalogService:
    ROLE_LABELS = {
        AIModelOption.RoleType.FAST: "Быстрая",
        AIModelOption.RoleType.BALANCED: "Сбалансированная",
        AIModelOption.RoleType.STRONG: "Сильная",
    }

    ROLE_HINTS = {
        AIModelOption.RoleType.FAST: ("flash-lite", "flash", "nano", "mini", "turbo", "small", "air", "haiku"),
        AIModelOption.RoleType.BALANCED: ("flash", "mini", "sonnet", "pro", "plus", "chat", "max"),
        AIModelOption.RoleType.STRONG: ("gpt-5", "gpt-4.1", "opus", "sonnet", "pro", "max", "reasoning"),
    }

    PREFERRED_PROVIDERS = ("openai/", "anthropic/", "google/", "x-ai/", "deepseek/", "qwen/", "z-ai/", "mistralai/")

    def __init__(self, provider=None):
        self.provider = provider or OpenRouterProvider()

    def get_active_options(self, *, auto_refresh=None):
        options = list(AIModelOption.objects.filter(is_active=True).order_by("role_type"))
        if len(options) >= 3:
            return options
        if auto_refresh is None:
            auto_refresh = settings.AI_AUTO_REFRESH_MODELS
        if auto_refresh:
            return self.refresh_catalog()
        return options

    def refresh_catalog(self):
        override_ids = {
            AIModelOption.RoleType.FAST: settings.OPENROUTER_MODEL_FAST,
            AIModelOption.RoleType.BALANCED: settings.OPENROUTER_MODEL_BALANCED,
            AIModelOption.RoleType.STRONG: settings.OPENROUTER_MODEL_STRONG,
        }
        live_models = self.provider.list_models()
        candidates = self._prepare_candidates(live_models)
        selected = self._select_models(candidates, override_ids=override_ids)
        return self._persist_selected_models(selected)

    def _prepare_candidates(self, live_models):
        prepared = []
        for item in live_models:
            model_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or model_id).strip()
            if not model_id or not self._is_chat_candidate(item):
                continue
            supports_structured_output = self._supports_structured_output(item)
            prepared.append(
                CandidateModel(
                    raw=item,
                    model_id=model_id,
                    name=name,
                    context_length=int(item.get("context_length") or 0),
                    supports_structured_output=supports_structured_output,
                    total_price=_decimal_or_zero((item.get("pricing") or {}).get("prompt"))
                    + _decimal_or_zero((item.get("pricing") or {}).get("completion")),
                )
            )
        return prepared

    def _is_chat_candidate(self, item):
        model_id = str(item.get("id") or "").lower()
        architecture = item.get("architecture") or {}
        input_modalities = [value.lower() for value in architecture.get("input_modalities") or []]
        output_modalities = [value.lower() for value in architecture.get("output_modalities") or []]
        if model_id.startswith("openrouter/"):
            return False
        if any(token in model_id for token in ("embed", "rerank", "tts", "whisper", "transcri", "moderation", "lyria")):
            return False
        if "text" not in input_modalities or "text" not in output_modalities:
            return False
        if int(item.get("context_length") or 0) < settings.AI_MIN_CONTEXT_WINDOW:
            return False
        return True

    def _supports_structured_output(self, item):
        supported_parameters = {value.lower() for value in item.get("supported_parameters") or []}
        return "structured_outputs" in supported_parameters or "response_format" in supported_parameters

    def _score_candidate(self, candidate, role_type):
        model_id = candidate.model_id.lower()
        name = candidate.name.lower()
        score = 0

        if candidate.supports_structured_output:
            score += 30
        if any(model_id.startswith(prefix) for prefix in self.PREFERRED_PROVIDERS):
            score += 15
        if candidate.context_length >= 128000:
            score += 12
        elif candidate.context_length >= 64000:
            score += 8
        elif candidate.context_length >= 32000:
            score += 4

        for hint in self.ROLE_HINTS[role_type]:
            if hint in model_id or hint in name:
                score += 18
                break

        if role_type == AIModelOption.RoleType.FAST:
            if any(token in model_id for token in ("lite", "nano", "turbo", "small", "air", "haiku")):
                score += 12
            if candidate.total_price <= Decimal("0.000002"):
                score += 40
            elif candidate.total_price <= Decimal("0.00001"):
                score += 22
            elif candidate.total_price <= Decimal("0.00003"):
                score += 8
            else:
                score -= 12
        elif role_type == AIModelOption.RoleType.BALANCED:
            if any(token in model_id for token in ("lite", "nano", "haiku", "air")):
                score -= 22
            if Decimal("0.000001") <= candidate.total_price <= Decimal("0.00004"):
                score += 18
            elif candidate.total_price <= Decimal("0.00008"):
                score += 12
        else:
            if any(token in model_id for token in ("lite", "nano", "mini", "haiku", "air", "small")):
                score -= 24
            if any(token in model_id for token in ("gpt-5", "gpt-4.1", "opus", "sonnet", "gemini-2.5-pro", "qwen-max", "deepseek-chat", "glm-5.1")):
                score += 28
            if candidate.total_price <= Decimal("0.0002"):
                score += 8

        if ":free" in model_id:
            score -= 8
        return score

    def _select_models(self, candidates, *, override_ids):
        chosen = {}
        remaining = list(candidates)

        for role_type, override_id in override_ids.items():
            if not override_id:
                continue
            override_candidate = next((item for item in remaining if item.model_id == override_id), None)
            if override_candidate:
                chosen[role_type] = override_candidate
                remaining = [item for item in remaining if item.model_id != override_id]

        for role_type in (
            AIModelOption.RoleType.FAST,
            AIModelOption.RoleType.BALANCED,
            AIModelOption.RoleType.STRONG,
        ):
            if role_type in chosen:
                continue
            ranked = sorted(
                remaining,
                key=lambda item: (self._score_candidate(item, role_type), item.context_length, -item.total_price),
                reverse=True,
            )
            if ranked:
                chosen[role_type] = ranked[0]
                remaining = [item for item in remaining if item.model_id != ranked[0].model_id]

        return chosen

    @transaction.atomic
    def _persist_selected_models(self, chosen):
        AIModelOption.objects.update(is_active=False)
        saved_options = []
        for role_type in (
            AIModelOption.RoleType.FAST,
            AIModelOption.RoleType.BALANCED,
            AIModelOption.RoleType.STRONG,
        ):
            candidate = chosen.get(role_type)
            if not candidate:
                continue
            option, _ = AIModelOption.objects.update_or_create(
                provider_name=candidate.provider_name,
                external_model_id=candidate.model_id,
                defaults={
                    "display_name": candidate.name,
                    "role_type": role_type,
                    "is_active": True,
                    "context_window": candidate.context_length,
                    "supports_structured_output": candidate.supports_structured_output,
                    "metadata_json": {
                        "role_label": self.ROLE_LABELS[role_type],
                        "pricing": candidate.raw.get("pricing") or {},
                        "top_provider": candidate.raw.get("top_provider") or {},
                        "supported_parameters": candidate.raw.get("supported_parameters") or [],
                    },
                },
            )
            if option.role_type != role_type or not option.is_active:
                option.role_type = role_type
                option.is_active = True
                option.save(update_fields=["role_type", "is_active", "updated_at"])
            saved_options.append(option)

        cache.set(CATALOG_CACHE_KEY, [option.pk for option in saved_options], settings.AI_MODEL_CACHE_SECONDS)
        return saved_options


def get_model_catalog_service():
    return ModelCatalogService()
