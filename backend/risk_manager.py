import os
from typing import Optional

from schemas import FinalDecision, MarketData


def apply_risk_filters(decision: FinalDecision, market_data: MarketData) -> FinalDecision:
    max_position_ratio = float(os.getenv("MAX_POSITION_SIZE", "0.10"))
    total_capital = float(os.getenv("ACCOUNT_EQUITY", "100000"))

    if decision.final_decision == "HOLD":
        decision.recommended_position_size = 0.0
        return decision

    position_dollar = total_capital * max_position_ratio
    decision.recommended_position_size = position_dollar

    min_stop_loss_distance = float(os.getenv("MIN_STOP_LOSS_DISTANCE", "0.03"))
    if decision.stop_loss is not None:
        distance = (market_data.current_price - decision.stop_loss) / market_data.current_price
        if distance < min_stop_loss_distance:
            adjusted_stop = market_data.current_price * (1.0 - min_stop_loss_distance)
            decision.stop_loss = adjusted_stop

    return decision
