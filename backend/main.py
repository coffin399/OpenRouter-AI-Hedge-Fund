import asyncio
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import broker_interface
import orchestrator
import risk_manager
from db import get_recent_trades, get_setting, set_setting
from openrouter_client import OpenRouterClient
from schemas import FinalDecision, MarketData, TradeResponse
from nodes import data_fetcher
import nisa_mode


app = FastAPI(title="OpenRouter AI Hedge Fund Backend")


class TradingModeUpdate(BaseModel):
    mode: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=FinalDecision)
async def analyze(market_data: MarketData) -> FinalDecision:
    return await orchestrator.run_analysis(market_data)


@app.post("/analyze/{symbol}", response_model=FinalDecision)
async def analyze_symbol(symbol: str) -> FinalDecision:
    market_data = await data_fetcher.fetch_market_data(symbol)
    return await orchestrator.run_analysis(market_data)


@app.post("/trade/{symbol}", response_model=TradeResponse)
async def trade_symbol(symbol: str) -> TradeResponse:
    market_data = await data_fetcher.fetch_market_data(symbol)
    decision = await orchestrator.run_analysis(market_data)
    decision = risk_manager.apply_risk_filters(decision, market_data)
    try:
        order_id = broker_interface.execute_trade(symbol, market_data, decision)
    except Exception:
        order_id = None
    return TradeResponse(symbol=symbol, decision=decision, order_id=order_id)


@app.get("/models")
async def list_models() -> List[Dict[str, Any]]:
    client = OpenRouterClient()
    models = await client.list_models(free_only=False)
    return models


@app.get("/models/free")
async def list_free_models() -> List[Dict[str, Any]]:
    client = OpenRouterClient()
    models = await client.list_models(free_only=True)
    return models


@app.get("/models/{model_id}/is_free")
async def is_free_model(model_id: str) -> Dict[str, Any]:
    client = OpenRouterClient()
    is_free = await client.is_free_model(model_id)
    return {"model_id": model_id, "is_free": is_free}


@app.get("/config/trading_mode")
async def get_trading_mode() -> Dict[str, str]:
    mode = get_setting("TRADING_MODE", os.getenv("TRADING_MODE", "virtual")) or "virtual"
    return {"mode": mode}


@app.post("/config/trading_mode")
async def set_trading_mode(payload: TradingModeUpdate) -> Dict[str, str]:
    mode = payload.mode.lower()
    if mode not in {"virtual", "paper", "live"}:
        raise HTTPException(status_code=400, detail="invalid trading mode")
    set_setting("TRADING_MODE", mode)
    return {"mode": mode}


@app.get("/trades/recent")
async def trades_recent(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        trades = get_recent_trades(limit=limit)
    except Exception:
        trades = []
    return trades


async def _polling_loop() -> None:
    symbols_raw = os.getenv("WATCH_SYMBOLS", "")
    symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()]
    if not symbols:
        return
    try:
        interval = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
    except ValueError:
        interval = 300
    auto_trade = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    nisa_symbols_raw = os.getenv("NISA_SYMBOLS", "")
    nisa_symbols = [s.strip() for s in nisa_symbols_raw.split(",") if s.strip()]
    while True:
        for symbol in symbols:
            try:
                market_data = await data_fetcher.fetch_market_data(symbol)
                decision = await orchestrator.run_analysis(market_data)
                decision = risk_manager.apply_risk_filters(decision, market_data)
                if auto_trade:
                    try:
                        broker_interface.execute_trade(symbol, market_data, decision)
                    except Exception:
                        continue
            except Exception:
                continue

        # NISA mode: simple periodic buying of specified funds
        for symbol in nisa_symbols:
            try:
                market_data = await data_fetcher.fetch_market_data(symbol)
                nisa_decision = nisa_mode.create_nisa_decision(symbol, market_data)
                if nisa_decision is not None and auto_trade:
                    broker_interface.execute_trade(symbol, market_data, nisa_decision)
            except Exception:
                continue
        await asyncio.sleep(interval)


@app.on_event("startup")
async def start_polling() -> None:
    asyncio.create_task(_polling_loop())
