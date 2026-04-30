-- Extension TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Table principale des trades
CREATE TABLE IF NOT EXISTS trades (
    event_time      TIMESTAMPTZ    NOT NULL,
    symbol          TEXT           NOT NULL,
    trade_id        BIGINT         NOT NULL,
    price           NUMERIC(18, 8) NOT NULL,
    quantity        NUMERIC(18, 8) NOT NULL,
    trade_time      TIMESTAMPTZ    NOT NULL,
    is_buyer_maker  BOOLEAN,
    inserted_at     TIMESTAMPTZ    DEFAULT now(),
    PRIMARY KEY (symbol, trade_id, event_time)
);

SELECT create_hypertable('trades', 'event_time', if_not_exists => TRUE);

-- Table des messages rejetés (validation échouée)
CREATE TABLE IF NOT EXISTS rejected_trades (
    received_at  TIMESTAMPTZ DEFAULT now(),
    reason       TEXT        NOT NULL,
    raw_payload  JSONB       NOT NULL
);
