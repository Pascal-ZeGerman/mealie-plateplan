"""Model registry: stable tier name -> provider, model ID, and pricing.

Tier names ("haiku", "sonnet", "opus", "gpt-4o-mini", "gpt-4o") are stable
identifiers. The underlying model_id can be updated without changing consumer code.

PRICING NOTES:
- Claude pricing: verified from official Anthropic docs 2026-02-25
- OpenAI pricing: ~$0.15/$0.60 per MTok (from training data; official page returned 403).
  Mark LOW_CONFIDENCE_OPENAI_PRICING = True — update before going to production.
"""

LOW_CONFIDENCE_OPENAI_PRICING = True  # Verify at platform.openai.com before production

MODEL_REGISTRY: dict[str, dict] = {
    "haiku": {
        "provider": "claude",
        "model_id": "claude-haiku-4-5-20251001",
        "input_cost_per_mtok": 1.0,    # $1/MTok input
        "output_cost_per_mtok": 5.0,   # $5/MTok output
        "display_name": "Claude Haiku 4.5 (fast, cheap)",
        "approx_cost_per_call": "~$0.002",
    },
    "sonnet": {
        "provider": "claude",
        "model_id": "claude-sonnet-4-6",
        "input_cost_per_mtok": 3.0,
        "output_cost_per_mtok": 15.0,
        "display_name": "Claude Sonnet 4.6 (balanced)",
        "approx_cost_per_call": "~$0.015",
    },
    "opus": {
        "provider": "claude",
        "model_id": "claude-opus-4-6",
        "input_cost_per_mtok": 5.0,
        "output_cost_per_mtok": 25.0,
        "display_name": "Claude Opus 4.6 (most capable)",
        "approx_cost_per_call": "~$0.05",
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "input_cost_per_mtok": 0.15,   # LOW_CONFIDENCE — verify at platform.openai.com
        "output_cost_per_mtok": 0.60,  # LOW_CONFIDENCE
        "display_name": "GPT-4o Mini (fast, very cheap)",
        "approx_cost_per_call": "~$0.0003",
    },
    "gpt-4o": {
        "provider": "openai",
        "model_id": "gpt-4o",
        "input_cost_per_mtok": 2.50,   # LOW_CONFIDENCE — verify at platform.openai.com
        "output_cost_per_mtok": 10.0,  # LOW_CONFIDENCE
        "display_name": "GPT-4o (capable)",
        "approx_cost_per_call": "~$0.01",
    },
}


def calculate_cost_usd(tier: str, input_tokens: int, output_tokens: int) -> float:
    """Pre-calculate cost at call time. Stored in ai_addon_ai_request_log for SUM queries."""
    config = MODEL_REGISTRY[tier]
    input_cost = (input_tokens / 1_000_000) * config["input_cost_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * config["output_cost_per_mtok"]
    return round(input_cost + output_cost, 8)


def get_model_id_for_tier(tier: str) -> str:
    return MODEL_REGISTRY[tier]["model_id"]


def get_provider_for_tier(tier: str) -> str:
    return MODEL_REGISTRY[tier]["provider"]


def list_tiers() -> list[dict]:
    """Return all tiers as a list suitable for admin dropdown UI."""
    return [
        {
            "tier": tier,
            "provider": meta["provider"],
            "model_id": meta["model_id"],
            "display_name": meta["display_name"],
            "approx_cost_per_call": meta["approx_cost_per_call"],
        }
        for tier, meta in MODEL_REGISTRY.items()
    ]
