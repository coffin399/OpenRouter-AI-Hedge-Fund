import json
import os
from typing import Any, Dict, List

from openrouter_client import OpenRouterClient
from schemas import MarketData, NodeRecommendation


RISK_MODEL_ENV = "RISK_MODEL"
DEFAULT_RISK_MODEL = "cohere/command-r-plus"


async def analyze(market_data: MarketData, client: OpenRouterClient) -> NodeRecommendation:
    model = os.getenv(RISK_MODEL_ENV, DEFAULT_RISK_MODEL)
    system_content = "You are a risk management expert for equity portfolios. Respond in JSON only."
    user_content = (
        "Evaluate the risk of taking a position in the following market data and return a JSON object with the keys: "
        "recommendation (BUY, SELL, HOLD), confidence (0-1), reasoning, target_price, stop_loss, holding_period.\n\n"
        f"Market data: {market_data.json()}"
    )
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    try:
        response = await client.chat(model=model, messages=messages)
        content = response["choices"][0]["message"]["content"]
        data: Dict[str, Any] = json.loads(content)
        recommendation = str(data.get("recommendation", "HOLD")).upper()
        if recommendation not in {"BUY", "SELL", "HOLD"}:
            recommendation = "HOLD"
        confidence = float(data.get("confidence", 0.5))
        reasoning = str(data.get("reasoning", ""))
        target_price = data.get("target_price")
        stop_loss = data.get("stop_loss")
        holding_period = data.get("holding_period")
    except Exception as exc:
        recommendation = "HOLD"
        confidence = 0.5
        reasoning = f"fallback_due_to_error: {exc}"
        target_price = None
        stop_loss = None
        holding_period = None
    return NodeRecommendation(
        node_id="risk_evaluation",
        model=model,
        recommendation=recommendation,
        confidence=confidence,
        reasoning=reasoning,
        target_price=target_price,
        stop_loss=stop_loss,
        holding_period=holding_period,
    )
