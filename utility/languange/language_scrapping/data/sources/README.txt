Manual source files live here. These are input seeds only.

Format for manual_seed.txt (pipe separated):
term|category|language|register|definition_id|definition_en|usage_examples(comma sep)|emotional_weight|distress_signal|escalation_flag|clinical_note|source|validated|added_date

Example:
capek hidup|L4|id|slang|Kelelahan eksistensial.|Existential exhaustion.|capek hidup banget,capek hidup terus|high|true|true|Needs calm exploration|S5|false|2026-05

CSV sources supported by the ingest script:
- colloquial-indonesian-lexicon.csv (columns: slang, formal, ...)
- slang_indo.csv.xls (two columns: slang, formal)
