import os
from typing import Any, Dict

import httpx

from db import get_recent_trades
from schemas import FinalDecision, MarketData


DISCORD_WEBHOOK_URL_ENV = "DISCORD_WEBHOOK_URL"
DISCORD_ENABLED_ENV = "DISCORD_ENABLED"


def _is_enabled() -> bool:
    enabled = os.getenv(DISCORD_ENABLED_ENV, "false").lower() == "true"
    url = os.getenv(DISCORD_WEBHOOK_URL_ENV)
    return enabled and bool(url)


def _build_performance_summary() -> str:
    try:
        trades = get_recent_trades(limit=100)
    except Exception:
        return "パフォーマンス情報を取得できませんでした。"
    if not trades:
        return "まだトレード履歴がありません。"
    total_trades = len(trades)
    realized_profits = [t.get("profit_loss") for t in trades if t.get("profit_loss") is not None]
    total_pnl = sum(realized_profits) if realized_profits else 0.0
    wins = [p for p in realized_profits if p > 0]
    win_rate = (len(wins) / len(realized_profits)) * 100.0 if realized_profits else 0.0
    avg_pnl = (total_pnl / len(realized_profits)) if realized_profits else 0.0
    return (
        f"総トレード数: {total_trades}\n"
        f"実現損益合計: {total_pnl:.2f}\n"
        f"勝率: {win_rate:.1f}%\n"
        f"平均損益: {avg_pnl:.2f}"
    )


def send_trade_notification(
    symbol: str,
    market_data: MarketData,
    decision: FinalDecision,
    order_id: str,
    trading_mode: str,
) -> None:
    if not _is_enabled():
        return
    url = os.getenv(DISCORD_WEBHOOK_URL_ENV)
    if not url:
        return

    side = "BUY" if decision.final_decision == "BUY" else "SELL"
    content_lines = [
        f"**AIトレード通知 ({trading_mode})**",
        f"銘柄: {symbol}",
        f"売買: {side}",
        f"現在価格: {market_data.current_price}",
        f"ターゲット価格: {decision.target_price}",
        f"ストップロス: {decision.stop_loss}",
        f"集約コンフィデンス: {decision.aggregate_confidence:.2f}",
        f"注文ID: {order_id}",
        "",
        "--- パフォーマンス指標 (recent) ---",
        _build_performance_summary(),
    ]
    payload: Dict[str, Any] = {"content": "\n".join(content_lines)}

    try:
        httpx.post(url, json=payload, timeout=10.0)
    except Exception:
        return
