import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2

from schemas import FinalDecision, NodeRecommendation


DATABASE_URL_ENV = "DATABASE_URL"


@contextmanager
def get_connection():
    url = os.getenv(DATABASE_URL_ENV)
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg2.connect(url)
    try:
        yield conn
    finally:
        conn.close()


def log_trade_decision(
    symbol: str,
    market_timestamp: str,
    decision: FinalDecision,
    entry_price: float,
    exit_price: Optional[float] = None,
    profit_loss: Optional[float] = None,
    holding_period_seconds: Optional[int] = None,
) -> None:
    node_votes: List[Dict[str, Any]] = []
    for node in decision.node_results:
        node_votes.append(
            {
                "node_id": node.node_id,
                "model": node.model,
                "recommendation": node.recommendation,
                "confidence": node.confidence,
            }
        )
    node_votes_json = json.dumps(node_votes)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trade_decisions (
                    timestamp,
                    symbol,
                    decision,
                    aggregate_confidence,
                    entry_price,
                    exit_price,
                    profit_loss,
                    holding_period,
                    node_votes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s::interval, %s::jsonb
                )
                """,
                (
                    datetime.utcnow(),
                    symbol,
                    decision.final_decision,
                    decision.aggregate_confidence,
                    entry_price,
                    exit_price,
                    profit_loss,
                    f"{holding_period_seconds or 0} seconds",
                    node_votes_json,
                ),
            )
        conn.commit()


def get_recent_trades(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    timestamp,
                    symbol,
                    decision,
                    aggregate_confidence,
                    entry_price,
                    exit_price,
                    profit_loss,
                    holding_period,
                    node_votes
                FROM trade_decisions
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        (
            trade_id,
            ts,
            symbol,
            decision,
            aggregate_confidence,
            entry_price,
            exit_price,
            profit_loss,
            holding_period,
            node_votes,
        ) = row
        results.append(
            {
                "id": trade_id,
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "symbol": symbol,
                "decision": decision,
                "aggregate_confidence": aggregate_confidence,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "profit_loss": profit_loss,
                "holding_period": str(holding_period),
                "node_votes": node_votes,
            }
        )
    return results
