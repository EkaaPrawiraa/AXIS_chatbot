"""langs ngisi dengan data"""

from agentic.agent.linguistic.corpus import (
    CorpusEntry,
    LinguisticCorpus,
    load_default_corpus,
)
from agentic.agent.linguistic.detector import (
    LinguisticSignals,
    detect_linguistic_signals,
)


__all__ = [
    "CorpusEntry",
    "LinguisticCorpus",
    "load_default_corpus",
    "LinguisticSignals",
    "detect_linguistic_signals",
]
