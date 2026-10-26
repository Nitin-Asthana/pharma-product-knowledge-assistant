# Evaluation

Evaluation is measured against `eval/questions.json`. Metrics are never fabricated; if Azure
credentials are missing the report says so instead of inventing numbers.

## Run

```powershell
python scripts/evaluate_rag.py
```

Results print as JSON and a detailed per-question breakdown is written to `eval/last_run.json`.

## Metrics

| Metric | Meaning |
| --- | --- |
| `intent_accuracy_pct` | Router classified the expected intent |
| `retrieval_recall_pct` | Expected product(s) appeared in retrieved evidence |
| `retrieval_precision_pct` | Share of retrieved products that were relevant |
| `groundedness_pct` | Answer supported by retrieved evidence |
| `citation_validity_pct` | Citations resolve to registered source URLs |
| `exact_fact_accuracy_pct` | Names / composition / category correct |
| `abstention_accuracy_pct` | Assistant abstains on unsupported / out-of-scope questions |
| `medical_safety_pct` | Patient-specific requests handled safely |

## Latest measured run (Azure live)

From `eval/last_run.json` (12 questions, `llm_available: true`):

| Metric | Value |
| --- | --- |
| intent_accuracy | 91.7% |
| retrieval_recall | 100.0% |
| retrieval_precision | 66.3% |
| citation_validity | 100.0% |
| exact_fact_accuracy | 100.0% |
| abstention_accuracy | 50.0% |
| medical_safety | 100.0% |
| groundedness | 100.0% |

### Notes on the numbers

- **Retrieval precision (66%)** reflects broad category/semantic questions that legitimately
  return several products; recall is prioritised for these.
- **Abstention (50%)** — the explicit out-of-scope question abstains correctly; the open
  meta-question ("what information isn't in the source?") retrieves loosely-related products
  and is a known limitation (see README limitations). These are honest measurements, not
  targets to be gamed.

Re-running ingestion or editing the question set will change these values; regenerate rather
than editing the numbers by hand.
