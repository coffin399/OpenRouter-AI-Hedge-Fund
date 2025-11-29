CREATE TABLE trade_decisions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    symbol VARCHAR(10),
    decision VARCHAR(10),
    aggregate_confidence FLOAT,
    entry_price FLOAT,
    exit_price FLOAT,
    profit_loss FLOAT,
    holding_period INTERVAL,
    node_votes JSONB
);

CREATE TABLE node_performance (
    node_id VARCHAR(50),
    model_name VARCHAR(100),
    total_decisions INT,
    accurate_decisions INT,
    accuracy_rate FLOAT,
    avg_profit FLOAT,
    last_updated TIMESTAMP
);

CREATE TABLE virtual_positions (
    symbol VARCHAR(10) PRIMARY KEY,
    quantity FLOAT,
    avg_price FLOAT,
    last_updated TIMESTAMP
);

CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
