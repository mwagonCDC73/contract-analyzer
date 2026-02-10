"""
API cost calculation and usage logging.

Pricing is based on Anthropic's published rates (as of 2025).
Update PRICING dict when rates change or new models are added.
"""

import logging

logger = logging.getLogger(__name__)

# Pricing per million tokens (USD)
PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    # Fallback for unknown models — uses Sonnet pricing
    "default": {"input": 3.00, "output": 15.00},
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD for a single API call."""
    rates = PRICING.get(model, PRICING["default"])
    cost = (input_tokens * rates["input"] / 1_000_000) + (output_tokens * rates["output"] / 1_000_000)
    return round(cost, 6)


def log_api_usage(
    supabase,
    contract_id: str,
    user_id: str,
    analysis_type: str,
    model_used: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost: float,
) -> None:
    """Insert a row into api_usage_logs."""
    supabase.table("api_usage_logs").insert({
        "contract_id": contract_id,
        "user_id": user_id,
        "analysis_type": analysis_type,
        "model_used": model_used,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost,
    }).execute()
