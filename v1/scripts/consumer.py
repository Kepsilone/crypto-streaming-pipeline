"""
Étape 4 — Kafka consumer → TimescaleDB + validation
Lit les messages du topic Kafka, valide chaque trade,
insère les valides dans trades et les invalides dans rejected_trades.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from decimal import Decimal

import asyncpg
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv
from loguru import logger

# Charger le .env depuis le dossier v1/
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Config
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC             = os.getenv("KAFKA_TOPIC", "crypto-trades")
KAFKA_GROUP_ID          = os.getenv("KAFKA_GROUP_ID", "crypto-consumer-group")
TIMESCALEDB_URL         = os.getenv("TIMESCALEDB_URL", "postgresql://user:password@localhost:5432/crypto")
LOG_LEVEL               = os.getenv("LOG_LEVEL", "INFO")

# Configuration loguru
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL, format="{time:HH:mm:ss} | {level} | {message}")

# Requête d'insertion — idempotente via ON CONFLICT DO NOTHING
INSERT_TRADE = """
    INSERT INTO trades (event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (symbol, trade_id, event_time) DO NOTHING
"""

INSERT_REJECTED = """
    INSERT INTO rejected_trades (reason, raw_payload)
    VALUES ($1, $2::jsonb)
"""

# Symbole attendu (en majuscules pour comparaison)
EXPECTED_SYMBOL = os.getenv("BINANCE_SYMBOL", "btcusdt").upper()


def validate_trade(trade: dict) -> None:
    """
    Valide un trade avant insertion.
    Lève ValueError avec la raison si le trade est invalide.

    Règles :
    - trade_id doit être présent et > 0
    - price doit être > 0
    - quantity doit être > 0
    - symbol doit correspondre au symbole attendu
    """
    if not trade.get("trade_id"):
        raise ValueError("trade_id manquant ou nul")

    if trade["price"] <= 0:
        raise ValueError(f"prix invalide : {trade['price']}")

    if trade["quantity"] <= 0:
        raise ValueError(f"quantité invalide : {trade['quantity']}")

    if trade["symbol"].upper() != EXPECTED_SYMBOL:
        raise ValueError(f"symbole inattendu : {trade['symbol']} (attendu: {EXPECTED_SYMBOL})")


def deserialize(raw_bytes: bytes) -> dict:
    """
    Désérialise un message Kafka en dict Python typé.
    - string ISO → datetime UTC aware
    - string     → Decimal pour price et quantity
    """
    data = json.loads(raw_bytes.decode("utf-8"))
    data["event_time"] = datetime.fromisoformat(data["event_time"])
    data["trade_time"] = datetime.fromisoformat(data["trade_time"])
    data["price"]      = Decimal(data["price"])
    data["quantity"]   = Decimal(data["quantity"])
    return data


async def insert_trade(conn: asyncpg.Connection, trade: dict) -> None:
    """Insère un trade valide dans TimescaleDB."""
    await conn.execute(
        INSERT_TRADE,
        trade["event_time"],
        trade["symbol"],
        trade["trade_id"],
        trade["price"],
        trade["quantity"],
        trade["trade_time"],
        trade["is_buyer_maker"],
    )


async def insert_rejected(conn: asyncpg.Connection, reason: str, raw: dict) -> None:
    """Insère un trade invalide dans rejected_trades avec sa raison et son payload brut."""
    await conn.execute(INSERT_REJECTED, reason, json.dumps(raw))


async def run() -> None:
    """
    Consomme le topic Kafka et insère chaque trade dans TimescaleDB.
    La connexion DB et le consumer Kafka sont initialisés une seule fois.
    """
    # Connexion TimescaleDB
    logger.info(f"[DB] Connexion à TimescaleDB...")
    conn = await asyncpg.connect(TIMESCALEDB_URL)
    logger.info("[DB] Connecté")

    # Consumer Kafka
    # auto_offset_reset="earliest" : relit depuis le début si le groupe n'a pas d'offset mémorisé
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info(f"[KAFKA] Consumer connecté → topic: {KAFKA_TOPIC} / group: {KAFKA_GROUP_ID}")

    try:
        async for msg in consumer:
            raw_data = {}
            try:
                raw_data = json.loads(msg.value.decode("utf-8"))
                trade = deserialize(msg.value)

                # Validation — lève ValueError si invalide
                validate_trade(trade)

                await insert_trade(conn, trade)
                logger.info(
                    f"[DB] Inséré trade_id={trade['trade_id']} | "
                    f"prix={trade['price']:.2f} | "
                    f"offset={msg.offset}"
                )

            except ValueError as e:
                # Trade invalide → rejected_trades
                reason = str(e)
                logger.warning(f"[REJET] offset={msg.offset} — {reason}")
                await insert_rejected(conn, reason, raw_data)

            except Exception as e:
                # Erreur technique → log sans planter le consumer
                logger.error(f"[DB] Erreur inattendue offset={msg.offset} : {e}")

    finally:
        await consumer.stop()
        await conn.close()
        logger.info("[DB] Connexion fermée proprement")


if __name__ == "__main__":
    logger.info("=== Consumer démarré ===")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("=== Consumer arrêté ===")
