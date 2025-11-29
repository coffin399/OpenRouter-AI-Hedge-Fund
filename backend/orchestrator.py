import asyncio
import os
from statistics import mean
from typing import Dict, List, Optional

from openrouter_client import OpenRouterClient
from schemas import FinalDecision, MarketData, NodeRecommendation
from nodes import fundamental_analysis, momentum_analysis, risk_evaluation, sentiment_analysis, technical_analysis


DEFAULT_WEIGHTS: Dict[str, float] = {
    "technical_analysis": 0.25,
    "fundamental_analysis": 0.20,
    "sentiment_analysis": 0.20,
    "risk_evaluation": 0.20,
    "momentum_analysis": 0.15,
}


def _aggregate_prices(node_results: List[NodeRecommendation]) -> (Optional[float], Optional[float]):
    targets = [r.target_price for r in node_results if r.target_price is not None]
    stops = [r.stop_loss for r in node_results if r.stop_loss is not None]
    target_price = mean(targets) if targets else None
    stop_loss = mean(stops) if stops else None
    return target_price, stop_loss


async def run_analysis(market_data: MarketData) -> FinalDecision:
    client = OpenRouterClient()
    tasks = [
        technical_analysis.analyze(market_data, client),
        fundamental_analysis.analyze(market_data, client),
        sentiment_analysis.analyze(market_data, client),
        risk_evaluation.analyze(market_data, client),
        momentum_analysis.analyze(market_data, client),
    ]
    node_results: List[NodeRecommendation] = await asyncio.gather(*tasks)
    votes: Dict[str, int] = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for result in node_results:
        votes[result.recommendation] += 1

    algo = os.getenv("DECISION_ALGORITHM", "weighted_majority")
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))

    if algo == "unanimous":
        non_hold = [r.recommendation for r in node_results if r.recommendation != "HOLD"]
        if non_hold and len(set(non_hold)) == 1:
            final_decision = non_hold[0]
            aggregate_confidence = min(1.0, sum(r.confidence for r in node_results) / len(node_results))
        else:
            final_decision = "HOLD"
            aggregate_confidence = 0.0
    else:
        buy_score = 0.0
        sell_score = 0.0
        weights = DEFAULT_WEIGHTS.copy()
        for result in node_results:
            weight = weights.get(result.node_id, 0.0)
            if result.recommendation == "BUY":
                buy_score += result.confidence * weight
            elif result.recommendation == "SELL":
                sell_score += result.confidence * weight
        if buy_score > threshold:
            final_decision = "BUY"
            aggregate_confidence = buy_score
        elif sell_score > threshold:
            final_decision = "SELL"
            aggregate_confidence = sell_score
        else:
            final_decision = "HOLD"
            aggregate_confidence = max(buy_score, sell_score)

    dissenting_opinions = []
    for result in node_results:
        if result.recommendation != final_decision:
            dissenting_opinions.append({"node": result.node_id, "reason": result.reasoning})

    target_price, stop_loss = _aggregate_prices(node_results)

    return FinalDecision(
        final_decision=final_decision,
        aggregate_confidence=aggregate_confidence,
        votes=votes,
        dissenting_opinions=dissenting_opinions or None,
        recommended_position_size=None,
        target_price=target_price,
        stop_loss=stop_loss,
        node_results=node_results,
    )
