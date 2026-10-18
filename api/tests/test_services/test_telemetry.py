import pytest
from unittest.mock import patch
from app.core.telemetry import TelemetryManager, QueryResponseCache, LangfuseBridge
from app.schemas.chat import ChatResponse


class TestTelemetry:
    def setup_method(self):
        self.mgr = TelemetryManager()

    def test_compute_cost(self):
        # 1,000 prompt tokens ($0.10/1M) = $0.00010
        # 500 completion tokens ($0.15/1M) = $0.000075
        # Total = $0.000175
        cost = self.mgr.compute_cost(1000, 500)
        assert cost == 0.000175

    def test_query_cache_set_and_get(self):
        cache = QueryResponseCache()
        cache.set("C-01", "What is CAGR?", "mock_response")
        
        # Exact match
        assert cache.get("C-01", "What is CAGR?") == "mock_response"
        # Case insensitive query match
        assert cache.get("c-01", "what is cagr?") == "mock_response"
        # Different client isolated
        assert cache.get("C-02", "What is CAGR?") is None

    def test_record_request_aggregates_metrics(self):
        self.mgr.record_request(
            client_id="C-01",
            question="What is 2024 market size?",
            intent="factual_lookup",
            latency_ms=120.5,
            prompt_tokens=400,
            completion_tokens=150,
            cache_hit=False,
            escalated=False,
            answer="USD 4.21B"
        )
        self.mgr.record_request(
            client_id="C-01",
            question="What is 2024 market size?",
            intent="cached_response",
            latency_ms=1.8,
            prompt_tokens=0,
            completion_tokens=0,
            cache_hit=True,
            escalated=False,
            answer="USD 4.21B"
        )

        metrics = self.mgr.get_summary_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["cache_hit_rate"] == "50.0%"
        assert metrics["total_tokens_consumed"] == 550
        assert metrics["langfuse_enabled"] is self.mgr.langfuse.enabled
        assert metrics["storage_footprint_mb"] == 0.0

    def test_langfuse_bridge_safe_when_unconfigured(self):
        with patch("app.core.telemetry.settings.LANGFUSE_PUBLIC_KEY", None), \
             patch("app.core.telemetry.settings.LANGFUSE_SECRET_KEY", None), \
             patch.dict("os.environ", {
                 "LANGFUSE_PUBLIC_KEY": "",
                 "LANGFUSE_SECRET_KEY": "",
             }):
            bridge = LangfuseBridge()
        assert bridge.enabled is False
        # Calling log_trace without credentials should not raise
        bridge.log_trace(
            trace_id="tr_test",
            client_id="C-01",
            question="test",
            answer="test",
            intent="factual_lookup",
            latency_ms=50.0,
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=0.00001
        )
