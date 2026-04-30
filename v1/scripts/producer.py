"""
Étape 2 — Binance WebSocket → Kafka
Lit les trades BTCUSDT en temps réel et les publie dans le topic Kafka.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

import websockets
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from loguru import logger

# Charger le .env depuis le dossier v1/
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Config
BINANCE_SYMBOL          = os.getenv("BINANCE_SYMBOL", "btcusdt").lower()
BINANCE_WS_URL          = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC             = os.getenv("KAFKA_TOPIC", "crypto-trades")
LOG_LEVEL               = os.getenv("LOG_LEVEL", "INFO")

WS_URL = f"{BINANCE_WS_URL}/{BINANCE_SYMBOL}@trade"

# Configuration loguru
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL, format="{time:HH:mm:ss} | {level} | {message}")


def ms_to_utc(ms: int) -> datetime:
    """Convertit un timestamp Binance (millisecondes Unix) en datetime UTC aware."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def parse_trade(raw: dict) -> dict:
    """
    Mappe le payload brut Binance vers un dict Python typé.
    price et quantity en Decimal — jamais en float.
    """
    return {
        "event_time":     ms_to_utc(raw["E"]),
        "symbol":         raw["s"],
        "trade_id":       int(raw["t"]),
        "price":          Decimal(raw["p"]),
        "quantity":       Decimal(raw["q"]),
        "trade_time":     ms_to_utc(raw["T"]),
        "is_buyer_maker": bool(raw["m"]),
    }


def serialize(trade: dict) -> bytes:
    """
    Sérialise le trade en JSON pour Kafka.
    - datetime → isoformat string (ex: "2024-01-01T14:23:01.123000+00:00")
    - Decimal  → string (ex: "68432.12000000") pour préserver la précision
    Le consumer reconvertira en Decimal avant insertion en base.
    """
    payload = {
        "event_time":     trade["event_time"].isoformat(),
        "symbol":         trade["symbol"],
        "trade_id":       trade["trade_id"],
        "price":          str(trade["price"]),
        "quantity":       str(trade["quantity"]),
        "trade_time":     trade["trade_time"].isoformat(),
        "is_buyer_maker": trade["is_buyer_maker"],
    }
    return json.dumps(payload).encode("utf-8")


async def handle_message(raw_msg: str, producer: AIOKafkaProducer) -> None:
    """Parse, affiche et publie dans Kafka un message Binance."""
    data = json.loads(raw_msg)

    # Ignorer les messages qui ne sont pas des trades
    if data.get("e") != "trade":
        logger.debug(f"Message ignoré (type={data.get('e')})")
        return

    trade = parse_trade(data)

    # Affichage console
    logger.info(
        f"[WS] {trade['symbol']} | "
        f"prix: {trade['price']:.2f} | "
        f"qté: {trade['quantity']:.8f} | "
        f"trade_id: {trade['trade_id']}"
    )

    # Publication dans Kafka
    # send_and_wait garantit que Kafka a bien reçu le message avant de continuer
    await producer.send_and_wait(KAFKA_TOPIC, serialize(trade))
    logger.info(f"[KAFKA] Publié trade_id={trade['trade_id']}")


async def run() -> None:
    """
    Connexion WebSocket avec reconnexion automatique (backoff exponentiel).
    Le producer Kafka est initialisé une seule fois et réutilisé.
    """
    # Initialisation du producer Kafka
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    logger.info(f"[KAFKA] Producer connecté → {KAFKA_BOOTSTRAP_SERVERS} / topic: {KAFKA_TOPIC}")

    delay = 1

    try:
        while True:
            try:
                logger.info(f"[WS] Connexion à {WS_URL}")
                async with websockets.connect(WS_URL) as ws:
                    delay = 1  # reset du délai si connexion réussie
                    logger.info(f"[WS] Connecté — flux {BINANCE_SYMBOL}@trade actif")

                    async for raw_msg in ws:
                        await handle_message(raw_msg, producer)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[WS] Connexion fermée : {e}. Reconnexion dans {delay}s...")
            except OSError as e:
                logger.warning(f"[WS] Erreur réseau : {e}. Reconnexion dans {delay}s...")
            except Exception as e:
                logger.error(f"[WS] Erreur inattendue : {e}. Reconnexion dans {delay}s...")

            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)

    finally:
        # Toujours fermer proprement le producer Kafka
        await producer.stop()
        logger.info("[KAFKA] Producer arrêté proprement")


if __name__ == "__main__":
    logger.info("=== Producer démarré ===")
    logger.info(f"Symbole : {BINANCE_SYMBOL.upper()}")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("=== Producer arrêté ===")
