import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from schemas import Fundamentals, MACD, MarketData, NewsSentimentItem, TechnicalIndicators


ALPHA_VANTAGE_API_KEY_ENV = "ALPHA_VANTAGE_API_KEY"
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


async def _get(params: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv(ALPHA_VANTAGE_API_KEY_ENV)
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is not set")
    query = params.copy()
    query["apikey"] = api_key
    async with httpx.AsyncClient(base_url=ALPHA_VANTAGE_BASE_URL, timeout=60.0) as client:
        response = await client.get("", params=query)
        response.raise_for_status()
        return response.json()


def _latest_entry(time_series: Dict[str, Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    latest_ts = max(time_series.keys())
    return latest_ts, time_series[latest_ts]


async def _fetch_intraday(symbol: str, interval: str = "5min") -> Optional[Tuple[str, Dict[str, Any]]]:
    data = await _get({
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "outputsize": "compact",
    })
    key = f"Time Series ({interval})"
    series = data.get(key)
    if not isinstance(series, dict):
        return None
    return _latest_entry(series)


async def _fetch_daily(symbol: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    data = await _get({
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "outputsize": "compact",
    })
    series = data.get("Time Series (Daily)")
    if not isinstance(series, dict):
        return None
    return _latest_entry(series)


async def _fetch_rsi(symbol: str, interval: str = "daily", time_period: int = 14) -> Optional[float]:
    data = await _get({
        "function": "RSI",
        "symbol": symbol,
        "interval": interval,
        "time_period": time_period,
        "series_type": "close",
    })
    series = data.get("Technical Analysis: RSI")
    if not isinstance(series, dict):
        return None
    latest_ts, latest = _latest_entry(series)
    value_str = latest.get("RSI")
    if value_str is None:
        return None
    return float(value_str)


async def _fetch_macd(symbol: str, interval: str = "daily") -> Optional[MACD]:
    data = await _get({
        "function": "MACD",
        "symbol": symbol,
        "interval": interval,
        "series_type": "close",
    })
    series = data.get("Technical Analysis: MACD")
    if not isinstance(series, dict):
        return None
    latest_ts, latest = _latest_entry(series)
    value_str = latest.get("MACD")
    signal_str = latest.get("MACD_Signal")
    if value_str is None or signal_str is None:
        return None
    return MACD(value=float(value_str), signal=float(signal_str))


async def _fetch_bbands(symbol: str, interval: str = "daily") -> Tuple[Optional[float], Optional[float]]:
    data = await _get({
        "function": "BBANDS",
        "symbol": symbol,
        "interval": interval,
        "time_period": 20,
        "series_type": "close",
    })
    series = data.get("Technical Analysis: BBANDS")
    if not isinstance(series, dict):
        return None, None
    latest_ts, latest = _latest_entry(series)
    upper_str = latest.get("Real Upper Band")
    lower_str = latest.get("Real Lower Band")
    upper = float(upper_str) if upper_str is not None else None
    lower = float(lower_str) if lower_str is not None else None
    return upper, lower


async def _fetch_fundamentals(symbol: str) -> Fundamentals:
    data = await _get({
        "function": "OVERVIEW",
        "symbol": symbol,
    })
    pe_ratio = data.get("PERatio")
    market_cap = data.get("MarketCapitalization")
    return Fundamentals(
        pe_ratio=float(pe_ratio) if pe_ratio not in (None, "") else None,
        market_cap=float(market_cap) if market_cap not in (None, "") else None,
    )


async def _fetch_news_sentiment(symbol: str) -> List[NewsSentimentItem]:
    try:
        data = await _get({
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "limit": 5,
        })
    except Exception:
        return []
    feed = data.get("feed")
    if not isinstance(feed, list):
        return []
    items: List[NewsSentimentItem] = []
    for entry in feed:
        title = entry.get("title") or entry.get("headline")
        sentiment = entry.get("overall_sentiment_score")
        if title is None or sentiment is None:
            continue
        try:
            score = float(sentiment)
        except Exception:
            continue
        items.append(NewsSentimentItem(headline=str(title), sentiment_score=score))
    return items


async def fetch_market_data(symbol: str) -> MarketData:
    intraday_task = asyncio.create_task(_fetch_intraday(symbol))
    daily_task = asyncio.create_task(_fetch_daily(symbol))
    rsi_task = asyncio.create_task(_fetch_rsi(symbol))
    macd_task = asyncio.create_task(_fetch_macd(symbol))
    bb_task = asyncio.create_task(_fetch_bbands(symbol))
    fundamentals_task = asyncio.create_task(_fetch_fundamentals(symbol))
    news_task = asyncio.create_task(_fetch_news_sentiment(symbol))

    intraday, daily, rsi_value, macd_value, (bb_upper, bb_lower), fundamentals, news = await asyncio.gather(
        intraday_task,
        daily_task,
        rsi_task,
        macd_task,
        bb_task,
        fundamentals_task,
        news_task,
    )

    timestamp: str
    current_price: float
    price_change_1d: Optional[float] = None
    price_change_1w: Optional[float] = None

    if intraday is not None:
        ts, point = intraday
        timestamp = datetime.fromisoformat(ts).isoformat()
        current_price = float(point.get("4. close"))
    elif daily is not None:
        ts, point = daily
        timestamp = datetime.fromisoformat(ts).isoformat()
        current_price = float(point.get("4. close"))
    else:
        raise RuntimeError("No price data available from Alpha Vantage")

    if daily is not None:
        _, latest_daily = daily
        close_today = float(latest_daily.get("4. close"))
        series_data = await _get({
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": "compact",
        })
        series = series_data.get("Time Series (Daily)") or {}
        sorted_dates = sorted(series.keys(), reverse=True)
        if len(sorted_dates) >= 2:
            prev_day = series[sorted_dates[1]]
            close_prev = float(prev_day.get("4. close"))
            if close_prev != 0:
                price_change_1d = (close_today - close_prev) / close_prev * 100.0
        if len(sorted_dates) >= 6:
            week_ago = series[sorted_dates[5]]
            close_week = float(week_ago.get("4. close"))
            if close_week != 0:
                price_change_1w = (close_today - close_week) / close_week * 100.0

    technical = TechnicalIndicators(
        rsi_14=rsi_value,
        macd=macd_value,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
    )

    volume: Optional[int] = None
    volume_avg_30d: Optional[int] = None

    if daily is not None:
        _, latest_daily = daily
        volume_str = latest_daily.get("6. volume")
        volume = int(volume_str) if volume_str is not None else None
        series_data = await _get({
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": "compact",
        })
        series = series_data.get("Time Series (Daily)") or {}
        sorted_dates = sorted(series.keys(), reverse=True)[:30]
        volumes: List[int] = []
        for d in sorted_dates:
            item = series[d]
            v_str = item.get("6. volume")
            if v_str is None:
                continue
            volumes.append(int(v_str))
        if volumes:
            volume_avg_30d = sum(volumes) // len(volumes)

    return MarketData(
        symbol=symbol,
        timestamp=timestamp,
        current_price=current_price,
        price_change_1d=price_change_1d,
        price_change_1w=price_change_1w,
        volume=volume,
        volume_avg_30d=volume_avg_30d,
        technical_indicators=technical,
        fundamentals=fundamentals,
        news_sentiment=news,
    )
