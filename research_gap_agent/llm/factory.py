"""
Returns a LangChain chat model for a given pipeline role. The role name
(e.g. "query_rewriter") is looked up in config.yaml, which says which
provider and model to use. Falls back to the "default" role when the
specific role is not configured.

Most providers (OpenAI, Anthropic, Google) work through `init_chat_model`.
NVIDIA and Groq expose OpenAI-compatible HTTP endpoints, so we route them
through ChatOpenAI with a custom base_url instead.
"""

from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from research_gap_agent.config import LLMRoleConfig, Secrets, load_settings


# Providers that expose an OpenAI-compatible HTTP API. We route these
# through ChatOpenAI + base_url instead of init_chat_model.
OPENAI_COMPATIBLE_PROVIDERS = {"nvidia", "groq", "openrouter", "vllm", "ollama"}


def api_key_for(provider: str, secrets: Secrets) -> Optional[str]:
    """Look up the API key for a given provider name."""
    keys = {
        "openai": secrets.openai_api_key,
        "anthropic": secrets.anthropic_api_key,
        "google_genai": secrets.google_api_key,
        "nvidia": secrets.nvidia_api_key,
        "groq": secrets.groq_api_key,
    }
    return keys.get(provider)


def build_llm(cfg: LLMRoleConfig, secrets: Secrets) -> BaseChatModel:
    api_key = api_key_for(cfg.provider, secrets)

    if cfg.provider in OPENAI_COMPATIBLE_PROVIDERS:
        # OpenAI-compatible endpoints (NVIDIA, Groq, OpenRouter, local vLLM).
        if not cfg.base_url:
            raise ValueError(
                f"Provider '{cfg.provider}' requires base_url in config.yaml."
            )
        if not api_key:
            raise ValueError(
                f"Provider '{cfg.provider}' requires an API key in .env."
            )

        return ChatOpenAI(
            model=cfg.model,
            api_key=api_key,
            base_url=cfg.base_url,
            temperature=cfg.temperature,
        )

    # Standard providers handled directly by langchain.
    kwargs = {
        "model": cfg.model,
        "model_provider": cfg.provider,
        "temperature": cfg.temperature,
    }
    if api_key is not None:
        kwargs["api_key"] = api_key
    if cfg.base_url is not None:
        kwargs["base_url"] = cfg.base_url

    return init_chat_model(**kwargs)


def get_llm(role: str = "default") -> BaseChatModel:
    settings = load_settings()
    cfg = settings.yaml.llm_for(role)
    return build_llm(cfg, settings.secrets)
