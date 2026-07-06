FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY agentic/requirements.txt ./agentic/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r ./agentic/requirements.txt

COPY agentic ./agentic

# agent/linguistic/corpus.py resolves this path 3 parents up from itself,
# i.e. relative to the repo root (not the agentic/ subdirectory) --
# without this the slang/distress-term corpus silently loads empty
# ("linguistic corpus not found ... using empty") and every corpus-driven
# signal (register, distress_terms) is unavailable for every message.
COPY utility/languange/data_ready_to_fed ./utility/languange/data_ready_to_fed

EXPOSE 8000

CMD ["python", "-m", "agentic.server.main"]
