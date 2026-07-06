```
AXIS_RUN_RESPONSE_MODEL_BENCHMARK=1 .venv/bin/python -m pytest -s agentic/tests/test_feature_bot/test_response_generator_model_benchmark.py
```

Kalau mau pakai pesan custom, bukan latest user message:

```
AXIS_RUN_RESPONSE_MODEL_BENCHMARK=1 \
AXIS_RESPONSE_MODEL_TEST_MESSAGE="Aku lagi ngerasa capek banget akhir-akhir ini." \
.venv/bin/python -m pytest -s agentic/tests/test_feature_bot/test_response_generator_model_benchmark.py
```

Kalau mau compare model tanpa tools:

```
AXIS_RUN_RESPONSE_MODEL_BENCHMARK=1 \
AXIS_RESPONSE_MODEL_TEST_USE_TOOLS=0 \
.venv/bin/python -m pytest -s agentic/tests/test_feature_bot/test_response_generator_model_benchmark.py

```