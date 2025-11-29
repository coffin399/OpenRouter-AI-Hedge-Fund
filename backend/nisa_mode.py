import os
from typing import Dict

from schemas import FinalDecision, MarketData, NodeRecommendation


def create_nisa_decision(symbol: str, market_data: MarketData) -> FinalDecision | None:
    """SIP/NISA-like simple decision.

    - Always BUY if enabled and price is below optional max price.
    - Invest fixed amount per run, controlled by NISA_INVEST_AMOUNT.
    """
    enabled = os.getenv("NISA_ENABLED", "false").lower() == "true"
    if not enabled:
        return None

    max_price_str = os.getenv("NISA_MAX_PRICE", "")
    if max_price_str:
        try:
            max_price = float(max_price_str)
            if market_data.current_price > max_price:
                return None
        except ValueError:
            pass

    invest_amount_str = os.getenv("NISA_INVEST_AMOUNT", "0")
    try:
        invest_amount = float(invest_amount_str)
    except ValueError:
        invest_amount = 0.0
    if invest_amount <= 0:
        return None

    votes: Dict[str, int] = {"BUY": 1, "SELL": 0, "HOLD": 0}

    return FinalDecision(
        final_decision="BUY",
        aggregate_confidence=1.0,
        votes=votes,
        dissenting_opinions=None,
        recommended_position_size=invest_amount,
        target_price=None,
        stop_loss=None,
        node_results=[],
    )
