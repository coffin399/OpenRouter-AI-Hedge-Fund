# OpenRouter AI Hedge Fund

AI マルチエージェントによる株式トレーディングシステムです。バックエンドは FastAPI + Python、フロントエンドは React + TypeScript で構成されています。

## 機能概要

- Alpha Vantage からのマーケットデータ取得
- OpenRouter 上の複数 LLM モデルによる 5 つの分析ノード
  - テクニカル分析
  - ファンダメンタル分析
  - センチメント分析
  - リスク評価
  - モメンタム分析
- 加重多数決 / 全会一致による最終売買判断
- リスク管理フィルタ（ポジションサイズ・ストップロス調整）
- Broker 連携
  - Alpaca Paper / Live
  - 仮想口座 (virtual) モード
- モード別運用
  - 通常トレードモード
  - NISA 風つみたてモード（指定ファンドへの定額投資）
- Discord Webhook によるトレード・簡易パフォーマンス通知
- React ダッシュボード

## トレードモード

`.env` の `TRADING_MODE` で 3 つのモードを切り替えます。

- `virtual`  : 架空口座。Broker API は呼ばず、DB ログと Discord 通知のみ。
- `paper`    : Alpaca Paper Trading API を使用。
- `live`     : Alpaca Live API を使用（実運用）。

全てのモードで `NISA` モードも動作します（virtual なら実資金は動きません）。

### NISA モード

- `.env`:
  - `NISA_ENABLED=true`
  - `NISA_SYMBOLS=VT` など、つみたて対象のファンド/ETF
  - `NISA_INVEST_AMOUNT=30000` など、1 回あたりの投資金額
  - `NISA_MAX_PRICE=` を指定すると、その価格より高い場合はスキップ
- ポーリングループから `NISA_SYMBOLS` 対して `NISA_INVEST_AMOUNT` を定期的に買い付けます。
- `TRADING_MODE=virtual` にしておけば、**完全に架空口座で挙動検証**が可能です。

## セットアップ

1. `.env.example` を `.env` にコピーし、API キー等を設定します。
2. Docker Desktop を起動します。
3. ルートディレクトリで:

```bash
# Windows
start.bat

# または
docker-compose up --build
```

4. アクセス

- Backend: `http://localhost:8000` (`/docs` で API 一覧)
- Frontend: `http://localhost:3000`

## 主要エンドポイント

- `GET /health` : ヘルスチェック
- `POST /analyze/{symbol}` : 指定銘柄の AI 分析
- `POST /trade/{symbol}` : AI 合議 + リスク管理 + Broker 経由でトレード
- `GET /trades/recent` : 直近トレード履歴

## 注意事項

- `TRADING_MODE=live` にする前に、必ず `virtual` / `paper` で十分な検証を行ってください。
- Discord 通知は `.env` の `DISCORD_ENABLED=true` と `DISCORD_WEBHOOK_URL` 設定が必要です。
