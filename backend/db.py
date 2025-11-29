import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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


def apply_virtual_fill(symbol: str, side: str, qty: float, price: float) -> Tuple[Optional[float], Optional[float]]:
    """Update virtual_positions and compute realized PnL for virtual trades.

    Returns (realized_pnl, entry_price_used).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT quantity, avg_price FROM virtual_positions WHERE symbol = %s",
                (symbol,),
            )
            row = cur.fetchone()
            if row:
                current_qty, avg_price = float(row[0] or 0.0), float(row[1] or 0.0)
            else:
                current_qty, avg_price = 0.0, 0.0

            realized_pnl: Optional[float] = None
            entry_price_used: Optional[float] = None

            if side == "BUY":
                new_qty = current_qty + qty
                if new_qty > 0:
                    new_avg = ((current_qty * avg_price) + (qty * price)) / new_qty
                else:
                    new_avg = price
                cur.execute(
                    """
                    INSERT INTO virtual_positions (symbol, quantity, avg_price, last_updated)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE
                    SET quantity = EXCLUDED.quantity,
                        avg_price = EXCLUDED.avg_price,
                        last_updated = EXCLUDED.last_updated
                    """,
                    (symbol, new_qty, new_avg, datetime.utcnow()),
                )
                entry_price_used = price
            else:  # SELL
                sell_qty = min(qty, current_qty) if current_qty > 0 else 0.0
                if sell_qty > 0 and current_qty > 0:
                    realized_pnl = (price - avg_price) * sell_qty
                    new_qty = current_qty - sell_qty
                    if new_qty <= 0:
                        cur.execute("DELETE FROM virtual_positions WHERE symbol = %s", (symbol,))
                    else:
                        cur.execute(
                            """
                            UPDATE virtual_positions
                            SET quantity = %s, last_updated = %s
                            WHERE symbol = %s
                            """,
                            (new_qty, datetime.utcnow(), symbol),
                        )
                    entry_price_used = avg_price
                else:
                    # no position to sell from
                    realized_pnl = 0.0
                    entry_price_used = price
        conn.commit()
    return realized_pnl, entry_price_used


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
            row = cur.fetchone()
    if row:
        return str(row[0])
    return default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                (key, value),
            )
        conn.commit()
