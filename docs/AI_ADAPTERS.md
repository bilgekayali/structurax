# v0.3 AI adapter boundary

StructuraX v0.3 adds a provider-neutral probabilistic extraction contract without
moving live model execution into the deterministic core.

## Boundary

The built-in `RecordedAIAdapter` is an offline replay adapter. It accepts an exact
`AIExtractionRequest` digest and returns a committed synthetic response. Its execution
profile is closed:

- `network_access: false`
- `tool_access: false`
- `subprocess_access: false`
- `filesystem_write_access: false`

A live provider integration is not shipped in v0.3. A deployment may implement the
same adapter protocol only behind a separately reviewed execution boundary. The core
contract does not grant network or tool permissions merely because an adapter calls
itself an AI provider.

## Request and provenance

`AIExtractionRequest` binds probabilistic extraction to:

- exact source SHA-256;
- exact v0.2 ingestion extraction SHA-256;
- bounded page text;
- a closed, canonical list of requested fields.

Recorded responses are keyed by the canonical request digest. Returned fields that
were not explicitly requested fail closed. Evidence pages must exist in the request.

## Prompt-injection handling

Document text is untrusted data. The coordinator scans the bounded request text for the
configured control-bypass indicators before invoking an adapter. A match causes a
`deterministic_fallback` resolution and the adapter is not invoked at all.

This is a deliberately narrow regression control, not a claim to detect every prompt
injection technique. Real deployments still require layered isolation, prompt design,
content handling and model-specific testing.

## Confidence and abstention

`AITrustPolicy` defines minimum overall and field confidence thresholds. The resolution
falls back when:

- overall confidence is below threshold;
- a required field is missing;
- a required field is below the field-confidence threshold; or
- untrusted instruction content is detected.

Passing the threshold does not authorize an operational action. Even `ai_selected`
results carry:

- `requires_human_review: true`;
- `automation_authority: false`;
- `operational_side_effects_performed: false`.

The deterministic fallback is represented by an exact artifact SHA-256. v0.3 does not
claim that the fallback establishes source authenticity or contractual truth.

## Synthetic benchmark

`datasets/ai/benchmark_cases.json` and the two `recorded_adapter_*.json` catalogs are
synthetic fixtures. The benchmark compares:

- exact field accuracy;
- evidence digest fidelity;
- fallback count;
- invocation count;
- recorded latency; and
- recorded cost.

The provider/model labels are synthetic reference labels. The benchmark performs no
live network/model call and must not be interpreted as a vendor ranking.

Regenerate the fixture set and benchmark:

```bash
python scripts/build_ai_fixtures.py
python scripts/evaluate_ai_adapters.py
```

Or exercise one case through the CLI:

```bash
structurax ai-replay \
  --cases datasets/ai/benchmark_cases.json \
  --case-id clean-invoice \
  --recordings datasets/ai/recorded_adapter_a.json \
  --output reports/local-ai-resolution.json
```

Compare both synthetic adapters:

```bash
structurax ai-benchmark \
  --cases datasets/ai/benchmark_cases.json \
  --recordings datasets/ai/recorded_adapter_a.json \
  --recordings datasets/ai/recorded_adapter_b.json \
  --output reports/local-ai-benchmark.json
```
