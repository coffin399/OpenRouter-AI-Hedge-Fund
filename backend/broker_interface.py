import os
import time
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from db import apply_virtual_fill, get_setting, log_trade_decision
from schemas import FinalDecision, MarketData
import discord_notifier


ALPACA_API_KEY_ENV = "ALPACA_API_KEY"
ALPACA_SECRET_KEY_ENV = "ALPACA_SECRET_KEY"
TRADING_MODE_ENV = "TRADING_MODE"


def _get_trading_client() -> TradingClient:
    api_key = os.getenv(ALPACA_API_KEY_ENV)
    secret_key = os.getenv(ALPACA_SECRET_KEY_ENV)
    if not api_key or not secret_key:
        raise RuntimeError("Alpaca API keys are not set")
    paper = os.getenv(TRADING_MODE_ENV, "paper") != "live"
    return TradingClient(api_key, secret_key, paper=paper)


def execute_trade(symbol: str, market_data: MarketData, decision: FinalDecision) -> Optional[str]:
    if decision.final_decision not in {"BUY", "SELL"}:
        return None
    if not decision.recommended_position_size or decision.recommended_position_size <= 0:
        return None

    qty = int(decision.recommended_position_size // market_data.current_price)
    if qty <= 0:
        return None

    mode = (get_setting("TRADING_MODE", os.getenv(TRADING_MODE_ENV, "paper")) or "paper").lower()

    if mode == "virtual":
        order_id = f"virtual-{symbol}-{int(time.time())}"
        side = "BUY" if decision.final_decision == "BUY" else "SELL"
        realized_pnl, entry_price_used = apply_virtual_fill(
            symbol=symbol,
            side=side,
            qty=qty,
            price=market_data.current_price,
        )
        log_trade_decision(
            symbol=symbol,
            market_timestamp=market_data.timestamp,
            decision=decision,
            entry_price=entry_price_used or market_data.current_price,
            exit_price=market_data.current_price if side == "SELL" else None,
            profit_loss=realized_pnl,
        )
        discord_notifier.send_trade_notification(
            symbol=symbol,
            market_data=market_data,
            decision=decision,
            order_id=order_id,
            trading_mode=mode,
        )
        return order_id

    client = _get_trading_client()
    side = OrderSide.BUY if decision.final_decision == "BUY" else OrderSide.SELL

    order_data = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=side,
        time_in_force=TimeInForce.DAY,
    )

    order = client.submit_order(order_data)

    log_trade_decision(
        symbol=symbol,
        market_timestamp=market_data.timestamp,
        decision=decision,
        entry_price=market_data.current_price,
    )

    discord_notifier.send_trade_notification(
        symbol=symbol,
        market_data=market_data,
        decision=decision,
        order_id=str(order.id),
        trading_mode=mode,
    )

    return str(order.id)
