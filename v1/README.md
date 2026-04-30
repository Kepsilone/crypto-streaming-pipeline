# Pipeline Streaming Crypto — V1

Pipeline temps réel BTCUSDT : Binance WebSocket → Kafka → TimescaleDB → FastAPI + Grafana.

Projet de portfolio — transition data engineering.

---

## Stack

| Composant     | Technologie                        |
|---------------|------------------------------------|
| Source        | Binance Spot WebSocket (public)    |
| Message broker| Apache Kafka 3.7 (KRaft, no Zookeeper) |
| Base de données | TimescaleDB (PostgreSQL 15 + hypertable) |
| API           | FastAPI + asyncpg                  |
| Dashboard     | Grafana 13                         |
| Runtime       | Python 3.11+ / asyncio / aiokafka  |
| Infra locale  | Docker Compose                     |

---

## Architecture

```
Binance WebSocket
      │  trades BTCUSDT en temps réel
      ▼
scripts/producer.py
      │  sérialise en JSON → Kafka topic "crypto-trades"
      ▼
Apache Kafka (KRaft)
      │  topic partitionné, group_id "crypto-consumer-group"
      ▼
scripts/consumer.py
      │  désérialise + valide (prix, quantité, symbol, trade_id)
      ├──► trades valides       → TimescaleDB (INSERT ON CONFLICT DO NOTHING)
      └──► trades invalides     → rejected_trades (raison + payload brut JSONB)
                ▼
         TimescaleDB
      ├──► src/api/app.py   → GET /health  /trades/latest  /trades/count
      └──► Grafana           → dashboard BTCUSDT temps réel (refresh 5s)
```

---

## Prérequis

- Docker Desktop
- Python 3.11+
- Clé API Binance : **aucune** — flux public, pas d'authentification

---

## Lancement

```bash
# 1. Cloner et configurer
git clone <repo>
cd pipeline-streaming-crypto/v1
cp .env.example .env        # éditer si besoin (valeurs par défaut suffisent en local)
pip install -r requirements.txt

# 2. Infra (Kafka + TimescaleDB + Grafana)
docker compose -f docker-compose.dev.yml up -d

# 3. Producer — lit Binance et publie dans Kafka
python scripts/producer.py

# 4. Consumer — lit Kafka, valide, insère en base
python scripts/consumer.py

# 5. API REST (optionnel)
python -m uvicorn src.api.app:app --reload --port 8000
```

---

## Services

| Service       | URL                              | Credentials    |
|---------------|----------------------------------|----------------|
| Grafana       | http://localhost:3000            | admin / admin  |
| FastAPI docs  | http://localhost:8000/docs       | —              |
| TimescaleDB   | localhost:5432 / db: crypto      | user / password|
| Kafka         | localhost:9092                   | —              |

---

## API endpoints

```
GET /health               → état API + connexion DB + count total
GET /trades/latest?n=50   → derniers N trades (défaut 50, max 500)
GET /trades/count         → nombre total de trades en base
```

---

## Schéma SQL

```sql
-- Trades valides (hypertable TimescaleDB)
trades (
    event_time      TIMESTAMPTZ    PK
    symbol          TEXT           PK
    trade_id        BIGINT         PK
    price           NUMERIC(18,8)
    quantity        NUMERIC(18,8)
    trade_time      TIMESTAMPTZ
    is_buyer_maker  BOOLEAN
    inserted_at     TIMESTAMPTZ    DEFAULT now()
)

-- Trades rejetés à la validation
rejected_trades (
    received_at  TIMESTAMPTZ  DEFAULT now()
    reason       TEXT          -- raison du rejet
    raw_payload  JSONB         -- payload brut Kafka
)
```

---

## Validation des trades (consumer)

Un trade est rejeté si :
- `price` ≤ 0
- `quantity` ≤ 0
- `trade_id` est absent ou nul
- `symbol` ne correspond pas à `BINANCE_SYMBOL` (défaut : BTCUSDT)

Les rejets sont tracés dans `rejected_trades` avec la raison en clair.

---

## Variables d'environnement

Voir `.env.example`. Les valeurs par défaut fonctionnent sans modification en développement local.

| Variable              | Défaut                    | Description                    |
|-----------------------|---------------------------|--------------------------------|
| `BINANCE_SYMBOL`      | `btcusdt`                 | Paire à suivre                 |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092`      | Adresse Kafka                  |
| `KAFKA_TOPIC`         | `crypto-trades`           | Topic Kafka                    |
| `KAFKA_GROUP_ID`      | `crypto-consumer-group`   | Consumer group                 |
| `TIMESCALEDB_URL`     | `postgresql://user:password@localhost:5432/crypto` | URL DB |
| `LOG_LEVEL`           | `INFO`                    | Niveau de logs (loguru)        |

---

## Structure du projet

```
v1/
├── scripts/
│   ├── producer.py          # Binance WS → Kafka
│   └── consumer.py          # Kafka → TimescaleDB + validation
├── src/
│   └── api/
│       └── app.py           # FastAPI : /health /trades/latest /trades/count
├── grafana/
│   └── provisioning/
│       ├── datasources/     # TimescaleDB auto-configuré
│       └── dashboards/      # Dashboard BTCUSDT chargé au démarrage
├── db/
│   └── migrations/
│       └── 001_init.sql     # DDL : trades + rejected_trades + hypertable
├── docker-compose.dev.yml
├── requirements.txt
└── .env.example
```

---

## Ce que démontre ce projet

- Ingestion temps réel via WebSocket avec reconnexion automatique (backoff exponentiel)
- Publication/consommation Kafka async (aiokafka, KRaft sans Zookeeper)
- Insertion idempotente dans une base time-series (TimescaleDB, `ON CONFLICT DO NOTHING`)
- Validation de données en pipeline avec circuit de rejet traçable
- API REST async (FastAPI + asyncpg, pool de connexions)
- Dashboard Grafana provisionné as-code (datasource + dashboard en YAML/JSON)
- Architecture procédurale V1 volontairement simple — refactor hexagonal prévu en V2

---

## Roadmap V2 (prévue)

Refactor vers une architecture hexagonale (Ports & Adapters) :
- `src/domain/` — entités Trade, règles métier
- `src/ports/` — interfaces MessageProducerPort, TradeRepositoryPort
- `src/adapters/` — implémentations Binance, Kafka, TimescaleDB
- Tests unitaires sur le domaine (sans infra)
- Multi-symboles configurables
- Métriques Prometheus + alerting
