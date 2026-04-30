# CLAUDE.md — pipeline-streaming-crypto
Fichier de contexte projet pour Claude. À placer à la racine du repo.

---

## Objectif du projet

Pipeline streaming temps réel basé sur des données publiques de marché crypto.
Le but n'est pas le trading, mais la démonstration d'une architecture data engineering
événementielle : ingestion WebSocket, transport Kafka, stockage time-series, API de lecture
et dashboard de monitoring.

Ce projet est un portfolio data engineering. Il reproduit une architecture applicable
au monitoring industriel, aux logs machines ou aux flux IoT.
La crypto n'est qu'une source de données temps réel gratuite, publique et documentée.

---

## Pattern architectural : Hexagonal Architecture (Ports & Adapters)

Choix courant en ingénierie logicielle, appliqué ici à un pipeline data engineering.
L'architecture hexagonale est utilisée comme exercice volontaire de structuration
logicielle pour rendre le pipeline testable, maintenable et extensible.
Ce choix est intentionnel sur un projet de cette taille — il ne serait pas justifié
en production sans exigences de maintenabilité, testabilité ou évolutivité.

Principe :
- Le domaine (entités, règles métier) ne connaît pas l'infrastructure.
- Les ports définissent des contrats (Python Protocols).
- Les adapters implémentent ces contrats pour chaque technologie.
- Les services orchestrent les flux en dépendant uniquement des ports.

Bénéfices concrets sur ce projet :
- Remplacer Kafka par Pulsar → seul l'adapter kafka/ change.
- Remplacer TimescaleDB par InfluxDB → seul l'adapter timescaledb/ change.
- Tester les services → mocker les ports, zéro infra requise.
- Onboarder un nouveau dev → il lit domain/ et ports/, comprend tout sans toucher Docker.

```
┌─────────────────────────────────────────────────────────────┐
│                        DOMAIN                               │
│            entities.py · exceptions.py                     │
│         (aucune dépendance externe — pur Python)            │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ utilise
┌─────────────────────────────────────────────────────────────┐
│                        PORTS                                │
│  StreamReaderPort · MessageProducerPort · TradeRepoPort     │
│  MessageConsumerPort (ports séparés producer / consumer)    │
│              (Python Protocols — contrats purs)             │
└─────────────────────────────────────────────────────────────┘
              ▲                              ▲
    implémente │                            │ implémente
┌──────────────────────┐       ┌────────────────────────────┐
│      ADAPTERS        │       │         ADAPTERS           │
│  binance/            │       │  kafka/  timescaledb/      │
│  websocket_reader.py │       │  producer.py  repo.py      │
└──────────────────────┘       └────────────────────────────┘
              ▲                              ▲
              └──────────┐   ┌──────────────┘
                         │   │
              ┌──────────────────────┐
              │       SERVICES       │
              │  ingestion_service   │
              │  processing_service  │
              │  validation_service  │
              └──────────────────────┘
                         ▲
                         │
              ┌──────────────────────┐
              │    ENTRYPOINTS       │
              │  scripts/producer.py │
              │  scripts/consumer.py │
              │  src/api/            │
              └──────────────────────┘
```

---

## Architecture du pipeline

```
Binance WebSocket (flux public)
        ↓
  BinanceWebSocketReader (adapter)
        ↓
  IngestionService (service)
        ↓
  KafkaProducer (adapter)  →  Kafka topic: crypto-trades
                                        ↓
                            KafkaConsumer (adapter)
                                        ↓
                            ProcessingService (service)
                                        ↓
                            ValidationService (service)
                            ↓              ↓
                    TimescaleDB       rejected_trades
                    Repository
                    (adapter)
                        ↓
              ┌─────────┴──────────┐
              ↓                    ↓
           FastAPI              Grafana
        lecture API        dashboard SQL direct
      (clients HTTP)    (datasource PostgreSQL)
```

Note : Grafana se connecte directement à TimescaleDB via le plugin PostgreSQL.
Il ne passe pas par FastAPI. Les deux sont des consommateurs indépendants de la base.
FastAPI sert les clients applicatifs (web, mobile, scripts).
Grafana sert la visualisation interne et l'observabilité.

---

## Stack technique

| Couche        | Technologie                    | Version        | Justification                                                  |
|---------------|--------------------------------|----------------|----------------------------------------------------------------|
| Source        | Binance Spot WebSocket Streams | public stream  | Flux temps réel public, pas d'auth requise                     |
| Ingestion     | Python + websockets            | 3.11+          | Bibliothèque légère, async natif                               |
| Transport     | Apache Kafka KRaft             | 3.x            | Découplage producer/consumer, sans Zookeeper                   |
| Stockage      | TimescaleDB                    | PostgreSQL 15  | Extension PostgreSQL, optimisée séries temporelles             |
| Exposition    | FastAPI                        | >= 0.111       | Async, typage, OpenAPI auto-généré                             |
| Visualisation | Grafana                        | latest         | Lecture SQL directe via datasource PostgreSQL                  |
| Infra         | Docker Compose                 | v2             | Reproductibilité, développement local                          |
| Config        | pydantic-settings              | >= 2.0         | Typage des variables d'environnement (voir note)               |
| Kafka client  | aiokafka                       | latest stable  | Client Kafka async — cohérent avec websockets et FastAPI       |
| DI            | factory functions              | —              | V1 : factories simples. dependency-injector en V2              |
| Logs          | loguru                         | >= 0.7         | Logs structurés JSON en production                             |
| Tests         | pytest + pytest-asyncio        | latest         | Tests unitaires et d'intégration                               |
| Style         | black + ruff                   | latest         | Formatage et linting                                           |

Note sur aiokafka vs kafka-python : kafka-python est synchrone. Utiliser kafka-python
dans un contexte async force l'usage de run_in_executor() ou de threads — c'est une
friction inutile. aiokafka expose une API async native compatible avec asyncio,
websockets et FastAPI sans adaptation.

---

## Structure du repo

```
pipeline-streaming-crypto/
│
├── src/                         # Code applicatif (hexagonale)
│   │
│   ├── domain/                  # Couche domaine — aucune dépendance externe
│   │   ├── __init__.py
│   │   ├── entities.py          # Trade, RejectedTrade (Pydantic BaseModel)
│   │   └── exceptions.py        # ValidationError, IngestionError, BrokerError
│   │
│   ├── ports/                   # Contrats (Python Protocols) — interfaces pures
│   │   ├── __init__.py
│   │   ├── stream_reader.py     # Protocol: connect(), read() -> AsyncIterator[dict]
│   │   ├── message_producer.py  # Protocol: publish(msg) — SÉPARÉ du consumer (voir note)
│   │   ├── message_consumer.py  # Protocol: consume() -> AsyncIterator — SÉPARÉ du producer
│   │   └── trade_repository.py  # Protocol: save(trade), save_rejected(trade, reason)
│   │
│   ├── adapters/                # Implémentations concrètes des ports
│   │   ├── __init__.py
│   │   ├── binance/
│   │   │   ├── __init__.py
│   │   │   └── websocket_reader.py  # Implémente StreamReaderPort
│   │   ├── kafka/
│   │   │   ├── __init__.py
│   │   │   ├── producer.py          # Implémente MessageProducerPort
│   │   │   └── consumer.py          # Implémente MessageConsumerPort
│   │   └── timescaledb/
│   │       ├── __init__.py
│   │       └── repository.py        # Implémente TradeRepositoryPort
│   │
│   ├── services/                # Logique métier — dépend uniquement des ports
│   │   ├── __init__.py
│   │   ├── ingestion_service.py   # Orchestre : reader → producer.publish()
│   │   ├── processing_service.py  # Orchestre : consumer.consume() → repo.save()
│   │   └── validation_service.py  # Valide un Trade, lève ValidationError si KO
│   │
│   └── api/                     # FastAPI — entrypoint HTTP
│       ├── __init__.py
│       ├── app.py               # Création de l'app FastAPI
│       ├── dependencies.py      # Injection des services via factory functions
│       └── routers/
│           ├── __init__.py
│           ├── health.py        # GET /health
│           ├── trades.py        # GET /trades/latest, /trades/count
│           └── metrics.py       # GET /metrics/ohlc, /metrics/volume, /metrics/latency
│
├── infrastructure/              # Configuration transversale
│   ├── __init__.py
│   ├── config.py                # pydantic-settings BaseSettings (lit .env)
│   ├── logging.py               # Configuration loguru (JSON en prod, lisible en dev)
│   └── factories.py             # Factory functions : instanciation adapters → services
│
├── db/
│   └── migrations/
│       └── 001_init.sql         # DDL : hypertable trades + rejected_trades
│
├── grafana/
│   ├── dashboards/
│   │   └── crypto.json          # Dashboard provisionné automatiquement
│   └── provisioning/
│       ├── datasources/
│       │   └── timescaledb.yaml
│       └── dashboards/
│           └── dashboards.yaml
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Fixtures : mocks des ports, DB de test
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_entities.py     # Sérialisation / validation des entités
│   │   ├── test_validation.py   # ValidationService — cas nominaux et rejets
│   │   └── test_services.py     # IngestionService / ProcessingService avec mocks
│   └── integration/
│       ├── __init__.py
│       ├── test_kafka.py        # Producer/consumer avec Kafka réel (Docker) — V2
│       ├── test_timescaledb.py  # Repository avec TimescaleDB réel (Docker) — V2
│       └── test_api.py          # Endpoints FastAPI avec TestClient
│
├── scripts/
│   ├── producer.py              # Entrypoint : instancie via factory, lance IngestionService
│   └── consumer.py              # Entrypoint : instancie via factory, lance ProcessingService
│
├── docs/
│   ├── architecture.md          # Schéma détaillé + justifications des choix
│   ├── decisions.md             # ADR (Architecture Decision Records)
│   └── apprentissage-phase1.md  # Notes d'apprentissage phase 1
│
├── docker-compose.yml           # Mode complet (tous services + app)
├── docker-compose.dev.yml       # Mode dev (infra seule : Kafka, TimescaleDB, Grafana)
├── Dockerfile.producer
├── Dockerfile.consumer
├── Dockerfile.api
├── requirements.txt             # Dépendances runtime (versions pinnées)
├── requirements-dev.txt         # pytest, black, ruff, mypy
├── pyproject.toml               # Config black, ruff, mypy, pytest
├── .env.example
├── .env                         # ignoré par git
├── .gitignore
├── README.md
└── CLAUDE.md                    # ce fichier
```

---

## Modèle de données

### src/domain/entities.py — Trade

```python
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field

class Trade(BaseModel):
    event_time:     datetime
    symbol:         str
    trade_id:       int
    price:          Decimal
    quantity:       Decimal
    trade_time:     datetime
    is_buyer_maker: bool
    # NOTE : datetime.now(timezone.utc) et non datetime.utcnow()
    # datetime.utcnow() est déprécié depuis Python 3.12 et retourne un datetime
    # sans timezone, ce qui cause des incohérences avec Kafka, TimescaleDB et Grafana
    # qui attendent des timestamps UTC explicitement typés.
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

### db/migrations/001_init.sql

```sql
-- Table principale
-- NOTE : NUMERIC(18, 8) et non NUMERIC seul.
-- Pour BTCUSDT en V1, les prix ont jusqu'à 8 décimales (ex: 68432.12345678).
-- NUMERIC sans précision est valide mais ambigu pour Grafana, psql et les ORMs.
-- NUMERIC(18, 8) : 18 chiffres au total, 8 après la virgule — suffisant pour BTC.
-- Si le projet passe en multi-symboles (V2), la précision devra être revue selon
-- les actifs : certaines petites cryptos ont des prix avec beaucoup plus de décimales.
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

-- Table rejet : tout message invalide est tracé ici avec sa raison et son payload brut.
-- Permet d'auditer la qualité de la source sans perdre de données.
CREATE TABLE IF NOT EXISTS rejected_trades (
    received_at  TIMESTAMPTZ DEFAULT now(),
    reason       TEXT        NOT NULL,
    raw_payload  JSONB       NOT NULL
);
```

### Règle d'insertion — idempotence

Les insertions dans `trades` doivent être idempotentes. Si le consumer redémarre
et rejoue des messages déjà traités, aucun doublon ne doit être inséré.

```sql
INSERT INTO trades (event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker)
VALUES (%(event_time)s, %(symbol)s, %(trade_id)s, %(price)s, %(quantity)s, %(trade_time)s, %(is_buyer_maker)s)
ON CONFLICT (symbol, trade_id, event_time) DO NOTHING;
```

`DO NOTHING` est préféré à `DO UPDATE` : un trade est immutable une fois reçu.
Mettre à jour un trade existant n'a pas de sens métier ici.

---

## Ports (contrats)

### Pourquoi deux ports Kafka séparés

Version initiale (incorrecte) :

```python
# MAUVAIS — un seul port pour producer ET consumer
class MessageBrokerPort(Protocol):
    async def publish(self, message: dict) -> None: ...
    def consume(self) -> AsyncIterator[dict]: ...
```

Problème : ce port oblige tout adapter Kafka à implémenter à la fois publish() et consume().
Un KafkaProducer n'a rien à faire avec consume(). Un KafkaConsumer n'a rien à faire
avec publish(). Cela viole le principe de ségrégation d'interfaces (ISP) et force
des méthodes vides ou des NotImplementedError dans chaque adapter.

Version correcte (deux ports distincts) :

```python
# src/ports/message_producer.py
class MessageProducerPort(Protocol):
    async def publish(self, message: dict) -> None: ...

# src/ports/message_consumer.py
class MessageConsumerPort(Protocol):
    async def consume(self) -> AsyncIterator[dict]: ...
    async def close(self) -> None: ...
```

Chaque adapter n'implémente que ce dont il a besoin.
IngestionService dépend de MessageProducerPort.
ProcessingService dépend de MessageConsumerPort.
Les deux sont mockables indépendamment dans les tests.

### src/ports/stream_reader.py

```python
class StreamReaderPort(Protocol):
    async def connect(self) -> None: ...
    async def read(self) -> AsyncIterator[dict]: ...
    async def close(self) -> None: ...
```

### src/ports/trade_repository.py

```python
class TradeRepositoryPort(Protocol):
    async def save(self, trade: Trade) -> None: ...
    async def save_rejected(self, reason: str, raw: dict) -> None: ...
    async def get_latest(self, n: int) -> list[Trade]: ...
    async def get_ohlc(self, interval: str) -> list[dict]: ...
```

---

## Mapping Binance payload → Trade

Le payload brut Binance ne doit jamais être propagé dans le domaine tel quel.
L'adapter `binance/websocket_reader.py` est le seul endroit qui connaît le format source.
Il convertit le message vers l'entité `Trade` avant de le transmettre au service.

Exemple de payload brut reçu depuis `btcusdt@trade` :

```json
{
  "e": "trade",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "t": 12345,
  "p": "68432.12000000",
  "q": "0.00100000",
  "T": 1672515782136,
  "m": true
}
```

Correspondance champ Binance → entité Trade :

| Champ Binance | Entité Trade   | Type cible              | Note                                     |
|--------------|----------------|-------------------------|------------------------------------------|
| E            | event_time     | datetime UTC            | millisecondes Unix → datetime aware      |
| s            | symbol         | str                     | tel quel, en majuscules                  |
| t            | trade_id       | int                     | identifiant unique du trade              |
| p            | price          | Decimal                 | string → Decimal (pas float, voir note)  |
| q            | quantity       | Decimal                 | string → Decimal                         |
| T            | trade_time     | datetime UTC            | millisecondes Unix → datetime aware      |
| m            | is_buyer_maker | bool                    | tel quel                                 |

Note sur Decimal vs float : Binance envoie les prix sous forme de string
("68432.12000000"). Convertir en float introduit des erreurs d'arrondi.
Toujours passer par Decimal pour price et quantity.

---

## Convention temporelle

Toutes les dates dans le domaine, la base et l'API sont en UTC timezone-aware.
Aucun `datetime` naïf (sans timezone) n'est autorisé dans le domaine.

Les timestamps Binance sont en millisecondes Unix. La conversion se fait dans
l'adapter, pas dans le service ni dans le domaine :

```python
from datetime import datetime, timezone

def _ms_to_utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
```

Cette règle complète la correction `datetime.utcnow()` → `datetime.now(timezone.utc)` :
les deux retournent des datetimes UTC explicitement typés, ce qui évite les
décalages silencieux dans TimescaleDB, Kafka et Grafana.

---

## Note sur pydantic-settings

Depuis Pydantic v2, BaseSettings est sorti du package principal pydantic.
Il faut installer et importer depuis pydantic-settings.

```txt
# requirements.txt
pydantic>=2.0
pydantic-settings>=2.0   ← obligatoire, sinon ImportError au démarrage
```

```python
# infrastructure/config.py
# CORRECT
from pydantic_settings import BaseSettings

# INCORRECT (Pydantic v1 uniquement — ne pas utiliser)
# from pydantic import BaseSettings
```

---

## Note sur dependency-injector

En V1, les factories simples suffisent. Pas besoin de dependency-injector.

```python
# infrastructure/factories.py — V1
def build_ingestion_service() -> IngestionService:
    reader   = BinanceWebSocketReader(settings.binance_ws_url, settings.binance_symbol)
    producer = KafkaTradeProducer(settings.kafka_bootstrap_servers, settings.kafka_topic)
    return IngestionService(reader=reader, producer=producer)

def build_processing_service() -> ProcessingService:
    consumer   = KafkaTradeConsumer(settings.kafka_bootstrap_servers, settings.kafka_topic)
    repository = TimescaleTradeRepository(settings.timescaledb_url)
    validator  = ValidationService()
    return ProcessingService(consumer=consumer, repository=repository, validator=validator)
```

dependency-injector apporte la configuration déclarative et le wiring automatique.
Pertinent en V2 si le graphe de dépendances devient complexe. Pas avant.

---

## Variables d'environnement (.env)

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=crypto-trades
KAFKA_GROUP_ID=crypto-consumer-group

# Source
BINANCE_SYMBOL=btcusdt
BINANCE_WS_URL=wss://stream.binance.com:9443/ws

# TimescaleDB
TIMESCALEDB_URL=postgresql://user:password@localhost:5432/crypto
TIMESCALEDB_POOL_SIZE=5

# API
API_HOST=0.0.0.0
API_PORT=8000

# Observability
LOG_LEVEL=INFO
LOG_FORMAT=json      # json (prod) | text (dev)
```

---

## Gestion de la résilience

| Problème                      | Traitement                                                |
|------------------------------|----------------------------------------------------------|
| WebSocket Binance coupé      | Reconnexion automatique, backoff exponentiel (adapter)   |
| Message invalide             | ValidationService lève ValidationError → rejected_trades |
| Kafka indisponible           | Retry + backoff dans l'adapter, log ERROR                |
| Doublon trade_id             | ON CONFLICT DO NOTHING (contrainte PRIMARY KEY)          |
| Consumer relancé             | Reprise depuis offset Kafka (group_id persisté)          |
| TimescaleDB indisponible     | Retry + backoff dans l'adapter, log ERROR                |

---

## Endpoints FastAPI — V1

| Endpoint                          | Description                           |
|----------------------------------|---------------------------------------|
| GET /health                      | État API + connexion DB               |
| GET /trades/latest?n=50          | Derniers N trades                     |
| GET /trades/count                | Nombre total de trades en base        |
| GET /metrics/ohlc?interval=1m    | Open / High / Low / Close             |
| GET /metrics/volume?interval=1m  | Volume échangé sur intervalle         |
| GET /metrics/latency             | Retard moyen ingestion (ms)           |
| GET /symbols                     | Symboles suivis                       |

---

## Priorité d'implémentation

Le projet doit être construit en flux vertical, pas couche par couche.

Règle fondamentale : aucune abstraction ne doit être ajoutée avant qu'un flux
réel ne fonctionne de bout en bout.

Pourquoi ? Parce que construire domain/, ports/, services/ et container.py avant
d'avoir un seul trade en base mène à 30 fichiers structurés mais rien de
démontrable. Le pipeline qui marche prime sur l'architecture propre.

Ordre d'implémentation :

| Étape | Objectif                                        | Livrable observable              |
|-------|-------------------------------------------------|----------------------------------|
| 1     | Lire Binance WebSocket                          | trades affichés dans le terminal |
| 2     | Publier dans Kafka                              | messages dans le topic           |
| 3     | Consommer Kafka                                 | messages lus côté consumer       |
| 4     | Insérer dans TimescaleDB                        | rows dans la table trades        |
| 5     | Ajouter validation + rejected_trades            | rejets tracés en base            |
| 6     | Ajouter FastAPI /health + /trades/latest        | API qui répond                   |
| 7     | Ajouter Grafana                                 | dashboard avec données réelles   |
| 8     | Refactorer en architecture hexagonale           | ports, adapters, services        |
| 9     | Ajouter tests unitaires (mocks des ports)       | pytest green                     |
| 10    | Finaliser portfolio                             | README, captures, article        |

Note sur l'étape 8 : la structure de fichiers hexagonale est créée dès le début
(dossiers déjà en place), mais le code interne peut rester procédural jusqu'à
l'étape 7. L'étape 8 est un refactor, pas une réécriture.

---

## Livrables par niveau

### V1 minimale — flux qui tourne

| Livrable                                          | Statut  |
|--------------------------------------------------|---------|
| Binance WebSocket → console                      | à faire |
| Kafka producer fonctionnel                       | à faire |
| Kafka consumer fonctionnel                       | à faire |
| Table trades hypertable                          | à faire |
| Insertion trades en base                         | à faire |
| Docker Compose dev (Kafka + TimescaleDB)         | à faire |
| Logs structurés                                  | à faire |

### V1 portfolio — projet montrable

| Livrable                                          | Statut  |
|--------------------------------------------------|---------|
| ValidationService + rejected_trades              | à faire |
| FastAPI /health + /trades/latest                 | à faire |
| Grafana dashboard prix + volume                  | à faire |
| Tests unitaires ValidationService               | à faire |
| README avec schéma d'architecture + captures    | à faire |

### V2 — architecture propre

| Livrable                                          | Statut  |
|--------------------------------------------------|---------|
| Ports séparés (MessageProducerPort/ConsumerPort) | à faire |
| Adapters découplés des services                  | à faire |
| Factory functions complètes                      | à faire |
| Tests unitaires services (mocks des ports)       | à faire |
| Tests d'intégration Kafka + TimescaleDB          | à faire |
| OHLC + latence + métriques avancées              | à faire |
| Grafana provisionné automatiquement              | à faire |
| Multi-symboles                                   | à faire |

---

## Règle de dépendance (stricte)

- domain/         → aucune dépendance externe
- ports/          → dépend uniquement de domain/
- adapters/       → dépend de ports/ + libs externes (aiokafka, asyncpg, websockets)
- services/       → dépend uniquement de ports/ et domain/
- api/            → dépend de services/ et domain/
- infrastructure/ → point d'assemblage, dépend de tout

---

## Règle anti-surcomplexité

Ne pas ajouter avant que la V1 portfolio soit terminée et démontrée :

- Apache Spark ou Flink
- Apache Airflow
- Kubernetes
- Modèle ML ou prédiction de prix
- Trading bot
- Authentification utilisateur
- Microservices supplémentaires
- Prometheus (V2)
- CI/CD GitHub Actions (V2)
- Déploiement cloud (V3)

Toute nouvelle brique doit répondre à un besoin direct et démontrable du pipeline.

---

## Hors périmètre définitif

- Trading automatique ou conseil en investissement
- Redistribution commerciale des données Binance
- Haute disponibilité Kafka (multi-broker, réplication)

---

## Lancement

### Mode développement (infra Docker, code local)

```bash
docker compose -f docker-compose.dev.yml up -d
python scripts/producer.py
python scripts/consumer.py
uvicorn src.api.app:app --reload
```

### Mode complet (tout dans Docker)

```bash
cp .env.example .env
docker compose up -d
```

---

## Conventions de développement

Branches :
- main        → stable uniquement
- develop     → intégration
- feature/xxx → développement actif

Commits (Conventional Commits) :
- feat:     nouvelle fonctionnalité
- fix:      correction de bug
- docs:     documentation uniquement
- chore:    maintenance, config
- refactor: refactoring sans changement fonctionnel

Style Python :
- black + ruff, type hints obligatoires sur toutes les signatures publiques
- loguru uniquement — jamais de print()
- Secrets via .env, jamais hardcodés
- pydantic-settings pour toute config (pas pydantic.BaseSettings — voir note)
- typing.Protocol pour tous les ports — pas d'ABC

---

## Auteur

Sabeur JEDID — Ingénieur process (LPBF/CETIM) en transition data engineering
Portfolio : kepsilone.com · GitHub : github.com/Kepsilone
