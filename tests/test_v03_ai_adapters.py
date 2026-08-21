from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from structurax.ai_adapters import (
    AIAdapterIdentity,
    AIAdapterResponse,
    AIExecutionProfile,
    AIExtractionRequest,
    AIFieldPrediction,
    AIPageInput,
    AITrustPolicy,
    DeterministicFallbackArtifact,
    RecordedAIAdapter,
    RecordedAIResponseCatalog,
    canonical_digest,
    resolve_ai_extraction,
    run_ai_extraction,
)
from structurax.ai_evaluation import AIBenchmarkSuite, evaluate_ai_adapters

AI_DIR = ROOT / 'datasets' / 'ai'


def load_catalog(name: str) -> RecordedAIAdapter:
    payload = json.loads((AI_DIR / name).read_text(encoding='utf-8'))
    return RecordedAIAdapter(RecordedAIResponseCatalog.model_validate(payload))


def load_suite() -> AIBenchmarkSuite:
    payload = json.loads((AI_DIR / 'benchmark_cases.json').read_text(encoding='utf-8'))
    return AIBenchmarkSuite.model_validate(payload)


class V03AIAdapterTests(unittest.TestCase):
    def test_execution_profile_is_closed(self) -> None:
        with self.assertRaises(ValidationError):
            AIExecutionProfile(network_access=True)
        with self.assertRaises(ValidationError):
            AIExecutionProfile(tool_access=True)

    def test_recorded_replay_binds_exact_request_digest(self) -> None:
        suite = load_suite()
        case = suite.cases[0]
        adapter = load_catalog('recorded_adapter_a.json')
        artifact = run_ai_extraction(case.request, adapter)
        self.assertEqual(artifact.request_sha256, canonical_digest(case.request.model_dump(mode='json')))
        self.assertFalse(artifact.external_execution_performed)
        self.assertTrue(artifact.requires_human_review)
        self.assertEqual(artifact.adapter.adapter_id, 'synthetic-adapter-a')

    def test_prompt_injection_blocks_adapter_invocation(self) -> None:
        suite = load_suite()
        case = next(item for item in suite.cases if item.case_id == 'prompt-injection-invoice')

        class SpyAdapter:
            def __init__(self) -> None:
                self.called = False
                self._identity = AIAdapterIdentity(
                    adapter_id='spy-adapter',
                    adapter_version='0.3.0',
                    provider_label='synthetic',
                    model_label='spy',
                )

            @property
            def identity(self):
                return self._identity

            def extract(self, request):
                self.called = True
                raise AssertionError('prompt-injection input must not invoke adapter')

        spy = SpyAdapter()
        resolution = resolve_ai_extraction(case.request, spy, AITrustPolicy(), case.fallback)
        self.assertFalse(spy.called)
        self.assertFalse(resolution.adapter_invoked)
        self.assertEqual(resolution.status, 'deterministic_fallback')
        self.assertIn('untrusted_instruction_detected:', resolution.reasons[0])

    def test_low_confidence_uses_deterministic_fallback(self) -> None:
        suite = load_suite()
        case = next(item for item in suite.cases if item.case_id == 'low-confidence-invoice')
        resolution = resolve_ai_extraction(
            case.request,
            load_catalog('recorded_adapter_a.json'),
            AITrustPolicy(),
            case.fallback,
        )
        self.assertTrue(resolution.adapter_invoked)
        self.assertEqual(resolution.status, 'deterministic_fallback')
        self.assertEqual(resolution.selected_artifact_sha256, case.fallback.artifact_sha256)
        self.assertIn('overall_confidence_below_threshold', resolution.reasons)

    def test_high_confidence_can_be_selected_but_never_auto_authorizes(self) -> None:
        suite = load_suite()
        case = next(item for item in suite.cases if item.case_id == 'clean-invoice')
        resolution = resolve_ai_extraction(
            case.request,
            load_catalog('recorded_adapter_a.json'),
            AITrustPolicy(),
            case.fallback,
        )
        self.assertEqual(resolution.status, 'ai_selected')
        self.assertTrue(resolution.requires_human_review)
        self.assertFalse(resolution.automation_authority)
        self.assertFalse(resolution.operational_side_effects_performed)

    def test_unrequested_fields_fail_closed(self) -> None:
        request = AIExtractionRequest(
            source_sha256='a' * 64,
            ingestion_extraction_sha256='b' * 64,
            pages=[AIPageInput(page_number=1, text='synthetic')],
            requested_fields=['invoice.total'],
        )
        response = AIAdapterResponse(
            fields=[AIFieldPrediction(
                field_name='bank.password',
                value='never',
                confidence=.99,
                evidence_pages=[1],
                evidence_text_sha256='c' * 64,
            )],
            overall_confidence=.99,
            latency_ms=1,
            cost_usd=0,
            provider_response_sha256='d' * 64,
        )

        class BadAdapter:
            @property
            def identity(self):
                return AIAdapterIdentity(
                    adapter_id='bad-adapter',
                    adapter_version='0.3.0',
                    provider_label='synthetic',
                    model_label='bad',
                )
            def extract(self, request):
                return response

        with self.assertRaisesRegex(ValueError, 'unrequested fields'):
            run_ai_extraction(request, BadAdapter())

    def test_evidence_digest_must_bind_cited_page_text(self) -> None:
        request = AIExtractionRequest(
            source_sha256='a' * 64,
            ingestion_extraction_sha256='b' * 64,
            pages=[AIPageInput(page_number=1, text='synthetic evidence')],
            requested_fields=['invoice.total'],
        )
        prediction = AIFieldPrediction(
            field_name='invoice.total',
            value='10.00',
            confidence=.99,
            evidence_pages=[1],
            evidence_text_sha256='c' * 64,
        )
        payload = {
            'fields': [prediction.model_dump(mode='json')],
            'overall_confidence': .99,
            'warnings': [],
            'latency_ms': 1,
            'cost_usd': 0,
        }
        response = AIAdapterResponse(
            **payload,
            provider_response_sha256=canonical_digest(payload),
        )

        class BadEvidenceAdapter:
            @property
            def identity(self):
                return AIAdapterIdentity(
                    adapter_id='bad-evidence-adapter',
                    adapter_version='0.3.0',
                    provider_label='synthetic',
                    model_label='bad-evidence',
                )
            def extract(self, request):
                return response

        with self.assertRaisesRegex(ValueError, 'evidence digest does not bind cited pages'):
            run_ai_extraction(request, BadEvidenceAdapter())

    def test_recorded_response_digest_is_recomputed(self) -> None:
        request = AIExtractionRequest(
            source_sha256='a' * 64,
            ingestion_extraction_sha256='b' * 64,
            pages=[AIPageInput(page_number=1, text='synthetic evidence')],
            requested_fields=['invoice.total'],
        )
        import hashlib
        evidence_digest = hashlib.sha256(b'synthetic evidence').hexdigest()
        response = AIAdapterResponse(
            fields=[AIFieldPrediction(
                field_name='invoice.total',
                value='10.00',
                confidence=.99,
                evidence_pages=[1],
                evidence_text_sha256=evidence_digest,
            )],
            overall_confidence=.99,
            latency_ms=1,
            cost_usd=0,
            provider_response_sha256='d' * 64,
        )

        class BadResponseDigestAdapter:
            @property
            def identity(self):
                return AIAdapterIdentity(
                    adapter_id='bad-response-digest-adapter',
                    adapter_version='0.3.0',
                    provider_label='synthetic',
                    model_label='bad-response-digest',
                )
            def extract(self, request):
                return response

        with self.assertRaisesRegex(ValueError, 'recorded response digest'):
            run_ai_extraction(request, BadResponseDigestAdapter())

    def test_benchmark_is_deterministic_and_compares_tradeoffs(self) -> None:
        suite = load_suite()
        adapters = [load_catalog('recorded_adapter_b.json'), load_catalog('recorded_adapter_a.json')]
        first = evaluate_ai_adapters(suite, adapters, AITrustPolicy())
        second = evaluate_ai_adapters(suite, adapters, AITrustPolicy())
        self.assertEqual(first, second)
        self.assertFalse(first.live_model_calls_performed)
        self.assertEqual([m.adapter_id for m in first.metrics], ['synthetic-adapter-a', 'synthetic-adapter-b'])
        a, b = first.metrics
        self.assertEqual(a.invocation_count, 2)
        self.assertEqual(a.fallback_count, 2)
        self.assertEqual(a.exact_field_accuracy, 0.6)
        self.assertEqual(b.fallback_count, 1)
        self.assertEqual(b.exact_field_accuracy, 0.8)
        self.assertEqual(b.evidence_fidelity, 1.0)

    def test_machine_contracts_publish_fail_closed_constants(self) -> None:
        resolution_schema = __import__('structurax.ai_adapters', fromlist=['AIResolution']).AIResolution.model_json_schema()
        props = resolution_schema['properties']
        self.assertEqual(props['schema_version']['const'], '0.3.0')
        self.assertFalse(props['automation_authority']['const'])
        self.assertFalse(props['operational_side_effects_performed']['const'])
        report_schema = __import__('structurax.ai_evaluation', fromlist=['AIAdapterBenchmarkReport']).AIAdapterBenchmarkReport.model_json_schema()
        self.assertFalse(report_schema['properties']['live_model_calls_performed']['const'])


if __name__ == '__main__':
    unittest.main()
