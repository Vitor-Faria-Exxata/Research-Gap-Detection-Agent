from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.yaml"


class LLMRoleConfig(BaseModel):
    provider: str
    model: str
    temperature: float = 0.3
    base_url: Optional[str] = None


class SourcesConfig(BaseModel):
    arxiv_enabled: bool = True
    openalex_enabled: bool = True
    semantic_scholar_enabled: bool = True


class PipelineConfig(BaseModel):
    num_queries: int = 5                    # N - queries generated from the topic
    top_papers: int = 20                    # X - top-ranked papers passed to extractor
    papers_per_query_per_source: int = 10   # how many papers each source returns per query
    request_timeout_s: int = 30
    max_workers: int = 8                    # ThreadPool size for the search step

class DocumentConverterConfig(BaseModel):
    provider_name: Literal['pymupdf', 'marker', 'jina'] = 'pymupdf'
    use_arxiv_html: bool = True

class YamlConfig(BaseModel):
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    llm: dict[str, LLMRoleConfig] = Field(default_factory=dict)
    document_converter: DocumentConverterConfig = Field(default_factory=DocumentConverterConfig)

    def llm_for(self, role: str) -> LLMRoleConfig:
        if role in self.llm:
            return self.llm[role]
        if "default" in self.llm:
            return self.llm["default"]
        raise KeyError(
            f"No LLM config for role '{role}' and no 'default' role in config.yaml."
        )


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    semantic_scholar_api_key: Optional[str] = None
    openalex_email: Optional[str] = None


class Settings(BaseModel):
    yaml: YamlConfig
    secrets: Secrets


_settings: Optional[Settings] = None


def load_settings(config_path: Optional[Path] = None) -> Settings:
    global _settings
    if _settings is not None and config_path is None:
        return _settings

    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {path}. "
            f"Check the repo root for the template."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    yaml_cfg = YamlConfig.model_validate(raw)
    secrets = Secrets()

    settings = Settings(yaml=yaml_cfg, secrets=secrets)
    if config_path is None:
        _settings = settings
    return settings
