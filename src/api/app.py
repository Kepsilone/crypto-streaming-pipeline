"""
Étape 5 — FastAPI : /health  /trades/latest  /trades/count
Application minimale — tout dans un seul fichier (V1).
"""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from loguru import logger

# Charger le .env depuis le dossier v1/
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Config
TIMESCALEDB_URL = os.getenv("TIMESCALEDB_URL", "postgresql://user:password@localhost:5432/crypto")
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO")

# Configuration loguru
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL, format="{time:HH:mm:ss} | {level} | {message}")

# Pool de connexions — initialisé au démarrage, fermé à l'arrêt
_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise le pool DB au démarrage, le ferme à l'arrêt."""
    global _pool
    logger.info("[DB] Création du pool de connexions...")
    _pool = await asyncpg.create_pool(TIMESCALEDB_URL, min_size=1, max_size=5)
    logger.info("[DB] Pool prêt")
    yield
    await _pool.close()
    logger.info("[DB] Pool fermé")


app = FastAPI(
    title="Crypto Pipeline API",
    description="API de consultation des trades BTCUSDT en temps réel",
    version="1.0.0",
    lifespan=lifespan,
)


def get_pool() -> asyncpg.Pool:
    """Retourne le pool ou lève une erreur si non initialisé."""
    if _pool is None:
        raise HTTPException(status_code=503, detail="Base de données non disponible")
    return _pool


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health", summary="État de l'API et de la base de données")
async def health() -> dict[str, Any]:
    """
    Vérifie que l'API tourne et que TimescaleDB est accessible.
    Retourne le nombre total de trades en base.
    """
    pool = get_pool()
    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM trades")
        return {
            "status": "ok",
            "database": "connected",
            "trades_count": count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"[HEALTH] Erreur DB : {e}")
        raise HTTPException(status_code=503, detail=f"DB error: {e}")


# ---------------------------------------------------------------------------
# GET /trades/latest
# ---------------------------------------------------------------------------

@app.get("/trades/latest", summary="Derniers N trades")
async def trades_latest(
    n: int = Query(default=50, ge=1, le=500, description="Nombre de trades à retourner"),
) -> list[dict[str, Any]]:
    """
    Retourne les N derniers trades triés par event_time DESC.
    price et quantity sont retournés en string pour préserver la précision Decimal.
    """
    pool = get_pool()
    try:
        rows = await pool.fetch(
            """
            SELECT event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker
            FROM trades
            ORDER BY event_time DESC
            LIMIT $1
            """,
            n,
        )
        return [
            {
                "event_time":     row["event_time"].isoformat(),
                "symbol":         row["symbol"],
                "trade_id":       row["trade_id"],
                "price":          str(row["price"]),
                "quantity":       str(row["quantity"]),
                "trade_time":     row["trade_time"].isoformat(),
                "is_buyer_maker": row["is_buyer_maker"],
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"[API] /trades/latest erreur : {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /trades/count
# ---------------------------------------------------------------------------

@app.get("/trades/count", summary="Nombre total de trades")
async def trades_count() -> dict[str, int]:
    """Retourne le nombre total de trades insérés en base."""
    pool = get_pool()
    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM trades")
        return {"count": count}
    except Exception as e:
        logger.error(f"[API] /trades/count erreur : {e}")
        raise HTTPException(status_code=500, detail=str(e))
