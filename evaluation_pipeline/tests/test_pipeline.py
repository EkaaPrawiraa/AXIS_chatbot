from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


PIPELINE_DIR = Path(__file__).resolve().parents[1]
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from config import EvaluationConfig
from metrics import aggregate_scores, score_transcript
from scenarios import SCENARIOS, select_scenarios


class ScenarioTests(unittest.TestCase):
    def test_scenario_ids_are_unique(self) -> None:
        ids = [scenario.id for scenario in SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_research_question_is_covered(self) -> None:
        self.assertEqual(
            {scenario.research_question for scenario in SCENARIOS},
            {"RM1", "RM2", "RM3"},
        )

    def test_axis_only_scenario_is_not_a_baseline_claim(self) -> None:
        phq = select_scenarios(["rm2_phq9_conversational"])[0]
        self.assertEqual(phq.scope, "axis_only")
        self.assertTrue(phq.expected_phq_item9_flagged)


class MetricTests(unittest.TestCase):
    def test_memory_mentions_and_safety_are_counted(self) -> None:
        scenario = select_scenarios(["rm3_memory_continuity_and_shift"])[0]
        records = [
            {
                "assistant": "Kamu pernah cerita soal Bab 3 dan dosen pembimbing.",
                "latency_ms": 100,
                "retrieved_memories": [
                    {"content": "Bimbingan Bab 3 dengan dosen pembimbing"}
                ],
                "kg_context": "context",
            },
            {
                "assistant": "Sekarang kita fokus ke minat backend kamu.",
                "latency_ms": 200,
                "retrieved_memories": [],
                "kg_context": "context",
            },
        ]
        score = score_transcript(records, scenario)
        self.assertEqual(score["expected_memory_term_turns"]["bab 3"], [1])
        self.assertEqual(score["kg_context_turns"], 2)
        self.assertEqual(score["latency_ms"]["mean"], 150)

    def test_aggregate_tracks_failed_repetitions(self) -> None:
        score = {
            "latency_ms": {"mean": None},
            "adjacent_response_jaccard": {"mean": None},
            "clinical_claim_count": 0,
            "safety_resource_present": False,
            "safety_expectation_met": True,
            "phq9_item9_expectation_met": True,
            "errors": ["boom"],
        }
        aggregate = aggregate_scores(
            [
                {
                    "system": "axis",
                    "scenario_id": "sample",
                    "metrics": score,
                }
            ]
        )
        self.assertEqual(aggregate["axis::sample"]["successful_repetitions"], 0)


class ConfigTests(unittest.TestCase):
    def test_public_snapshot_excludes_secrets(self) -> None:
        config = EvaluationConfig(
            database_url="postgres://secret",
            neo4j_uri="bolt://localhost",
            neo4j_username="neo4j",
            neo4j_password="secret",
            neo4j_database="neo4j",
            baseline_provider="gemini",
            baseline_model="model",
            baseline_base_url="https://example.test",
            baseline_api_key="secret",
            baseline_temperature=0.7,
            baseline_max_tokens=100,
            simulator_provider="gemini",
            simulator_model="simulator",
            simulator_base_url="https://example.test",
            simulator_api_key="secret",
            simulator_temperature=0.8,
            simulator_max_tokens=100,
            axis_provider="gemini",
            embedding_provider="gemini",
            embedding_model="embedding",
            embedding_dimension=1536,
            top_k=5,
            random_seed=42,
            send_provider_seed=False,
            repetitions=3,
            request_timeout_seconds=30,
            results_dir=Path("runs"),
        )
        snapshot = config.public_snapshot()
        rendered = repr(snapshot)
        self.assertNotIn("postgres://secret", rendered)
        self.assertNotIn("baseline_api_key", snapshot)
        self.assertNotIn("simulator_api_key", snapshot)
        self.assertNotIn("neo4j_password", snapshot)


if __name__ == "__main__":
    unittest.main()
