from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MACD(BaseModel):
    value: float
    signal: float


class TechnicalIndicators(BaseModel):
    rsi_14: Optional[float] = None
    macd: Optional[MACD] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None


class Fundamentals(BaseModel):
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None


class NewsSentimentItem(BaseModel):
    headline: str
    sentiment_score: float


class MarketData(BaseModel):
    symbol: str
    timestamp: str
    current_price: float
    price_change_1d: Optional[float] = None
    price_change_1w: Optional[float] = None
    volume: Optional[int] = None
    volume_avg_30d: Optional[int] = None
    technical_indicators: Optional[TechnicalIndicators] = None
    fundamentals: Optional[Fundamentals] = None
    news_sentiment: Optional[List[NewsSentimentItem]] = None


class NodeRecommendation(BaseModel):
    node_id: str
    model: str
    recommendation: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    holding_period: Optional[str] = None


class FinalDecision(BaseModel):
    final_decision: Literal["BUY", "SELL", "HOLD"]
    aggregate_confidence: float
    votes: Dict[str, int]
    dissenting_opinions: Optional[List[Dict[str, str]]] = None
    recommended_position_size: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    node_results: List[NodeRecommendation]


class TradeResponse(BaseModel):
    symbol: str
    decision: FinalDecision
    order_id: Optional[str] = None
