"""Evaluation pipeline configuration."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
load_dotenv(PIPELINE_DIR / ".env", override=False)
load_dotenv(REPO_ROOT / "agentic" / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    return int(_env(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(_env(name, str(default)))


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name, "1" if default else "0").lower()
    return value in {"1", "true", "yes", "on"}


def require_value(name: str, value: str) -> str:
    if not value:
        raise RuntimeError(
            f"Missing {name}. Add it to evaluation_pipeline/.env; "
            "do not commit the secret."
        )
    return value


@dataclass(frozen=True)
class EvaluationConfig:
    database_url: str
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str

    baseline_provider: str
    baseline_model: str
    baseline_base_url: str
    baseline_api_key: str
    baseline_temperature: float
    baseline_max_tokens: int

    simulator_provider: str
    simulator_model: str
    simulator_base_url: str
    simulator_api_key: str
    simulator_temperature: float
    simulator_max_tokens: int

    axis_provider: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    top_k: int

    random_seed: int
    send_provider_seed: bool
    repetitions: int
    request_timeout_seconds: float
    results_dir: Path

    @classmethod
    def from_env(cls) -> "EvaluationConfig":
        openai_key = _env("OPENAI_API_KEY")
        gemini_key = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")

        baseline_provider = _env("EVAL_BASELINE_PROVIDER", "gemini").lower()
        simulator_provider = _env("EVAL_SIMULATOR_PROVIDER", "gemini").lower()
        embedding_provider = _env("EVAL_EMBEDDING_PROVIDER", "gemini").lower()

        def provider_key(provider: str) -> str:
            if provider == "openai":
                return openai_key
            if provider in {"gemini", "google"}:
                return gemini_key
            return _env("LOCAL_LLM_API_KEY", "not-needed")

        def provider_url(provider: str) -> str:
            if provider == "openai":
                return ""
            if provider in {"gemini", "google"}:
                return _env(
                    "GEMINI_BASE_URL",
                    "https://generativelanguage.googleapis.com/v1beta/openai/",
                )
            return _env("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1")

        return cls(
            database_url=_env("DATABASE_URL"),
            neo4j_uri=_env("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_username=_env("NEO4J_USERNAME", "neo4j"),
            neo4j_password=_env("NEO4J_PASSWORD"),
            neo4j_database=_env("NEO4J_DATABASE", "neo4j"),
            baseline_provider=baseline_provider,
            baseline_model=_env("EVAL_BASELINE_MODEL", "gemini-3.5-flash"),
            baseline_base_url=provider_url(baseline_provider),
            baseline_api_key=provider_key(baseline_provider),
            baseline_temperature=_env_float("EVAL_BASELINE_TEMPERATURE", 0.7),
            baseline_max_tokens=_env_int("EVAL_BASELINE_MAX_TOKENS", 700),
            simulator_provider=simulator_provider,
            simulator_model=_env(
                "EVAL_SIMULATOR_MODEL", "gemini-3.1-flash-lite"
            ),
            simulator_base_url=provider_url(simulator_provider),
            simulator_api_key=provider_key(simulator_provider),
            simulator_temperature=_env_float("EVAL_SIMULATOR_TEMPERATURE", 0.8),
            simulator_max_tokens=_env_int("EVAL_SIMULATOR_MAX_TOKENS", 100),
            axis_provider=_env("EVAL_AXIS_PROVIDER", "gemini").lower(),
            embedding_provider=embedding_provider,
            embedding_model=_env(
                "EVAL_EMBEDDING_MODEL", "gemini-embedding-001"
            ),
            embedding_dimension=_env_int("EVAL_EMBEDDING_DIMENSION", 1536),
            top_k=_env_int("EVAL_TOP_K", 5),
            random_seed=_env_int("EVAL_RANDOM_SEED", 20260710),
            send_provider_seed=_env_bool("EVAL_SEND_PROVIDER_SEED", False),
            repetitions=_env_int("EVAL_REPETITIONS", 3),
            request_timeout_seconds=_env_float("EVAL_REQUEST_TIMEOUT_SECONDS", 90),
            results_dir=Path(
                _env("EVAL_RESULTS_DIR", str(PIPELINE_DIR / "runs"))
            ).expanduser(),
        )

    def validate_for(self, *, baseline: bool = False, axis: bool = False) -> None:
        require_value("DATABASE_URL", self.database_url)
        if baseline:
            require_value(
                f"API key for baseline provider {self.baseline_provider}",
                self.baseline_api_key,
            )
            require_value(
                f"API key for embedding provider {self.embedding_provider}",
                self._embedding_api_key(),
            )
        if axis and self.axis_provider not in {"openai", "gemini", "local"}:
            raise RuntimeError(f"Unsupported EVAL_AXIS_PROVIDER={self.axis_provider!r}")

    def _embedding_api_key(self) -> str:
        if self.embedding_provider == "openai":
            return _env("OPENAI_API_KEY")
        if self.embedding_provider in {"gemini", "google"}:
            return _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
        return "not-needed"

    def public_snapshot(self) -> dict[str, Any]:
        snapshot = asdict(self)
        for key in (
            "database_url",
            "neo4j_password",
            "baseline_api_key",
            "simulator_api_key",
        ):
            snapshot.pop(key, None)
        snapshot["results_dir"] = str(self.results_dir)
        snapshot["database_configured"] = bool(self.database_url)
        snapshot["neo4j_configured"] = bool(self.neo4j_password)
        snapshot["provider_seed_sent"] = self.send_provider_seed
        return snapshot


CONFIG = EvaluationConfig.from_env()

DATABASE_URL = CONFIG.database_url
DEFAULT_USER_ID = _env("USER_ID")
OPENAI_API_KEY = _env("OPENAI_API_KEY")
GEMINI_API_KEY = _env("GEMINI_API_KEY") or _env("GOOGLE_API_KEY")
CHAT_API_KEY = CONFIG.baseline_api_key
CHAT_BASE_URL = CONFIG.baseline_base_url
CHAT_MODEL = CONFIG.baseline_model
EMBEDDING_MODEL = CONFIG.embedding_model
EMBED_DIM = CONFIG.embedding_dimension
LLM_PROVIDER = CONFIG.baseline_provider
TOP_K_DEFAULT = CONFIG.top_k
