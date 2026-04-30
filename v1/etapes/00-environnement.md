# Étape 0 — Environnement

**Objectif :** avoir un repo Git propre avec les fichiers de base avant d'écrire du code.

**Durée estimée :** 20 minutes

---

## Fichiers à créer

```
pipeline-streaming-crypto/
├── .gitignore
├── .env.example
├── requirements.txt
└── docker-compose.dev.yml
```

---

## Contenu de chaque fichier

### .gitignore

```
# Python
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/

# Environnement
.env
venv/
.venv/

# IDE
.vscode/
.idea/
*.iml

# OS
.DS_Store
Thumbs.db

# Données locales
data/
*.db
```

---

### .env.example

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=crypto-trades
KAFKA_GROUP_ID=crypto-consumer-group

# Source Binance
BINANCE_SYMBOL=btcusdt
BINANCE_WS_URL=wss://stream.binance.com:9443/ws

# TimescaleDB
TIMESCALEDB_URL=postgresql://user:password@localhost:5432/crypto
TIMESCALEDB_POOL_SIZE=5

# API
API_HOST=0.0.0.0
API_PORT=8000

# Logs
LOG_LEVEL=INFO
LOG_FORMAT=text
```

---

### requirements.txt

```
# WebSocket
websockets==12.0

# Kafka async
aiokafka==0.11.0

# Base de données
asyncpg==0.29.0

# Validation et config
pydantic==2.7.1
pydantic-settings==2.2.1

# API
fastapi==0.111.0
uvicorn[standard]==0.29.0

# Logs
loguru==0.7.2
```

---

### docker-compose.dev.yml

```yaml
services:

  kafka:
    image: apache/kafka:3.7.0
    container_name: kafka
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
    ports:
      - "9092:9092"

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    container_name: timescaledb
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: crypto
    ports:
      - "5432:5432"
    volumes:
      - tsdb_data:/var/lib/postgresql/data
      - ./db/migrations:/docker-entrypoint-initdb.d

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    depends_on:
      - timescaledb

volumes:
  tsdb_data:
```

---

## Commandes Git à exécuter

```bash
cd pipeline-streaming-crypto
git init
git checkout -b main
git add .gitignore .env.example requirements.txt docker-compose.dev.yml CLAUDE.md
git commit -m "chore: initialisation du projet"
git checkout -b develop
```

---

## Vérification

Avant de passer à l'étape 1, vérifie :

- [ ] `git status` est propre sur `develop`
- [ ] `.env` n'est pas tracké (`git status` ne doit pas le montrer)
- [ ] `docker compose -f docker-compose.dev.yml up -d` lance les trois services sans erreur
- [ ] `docker ps` montre kafka, timescaledb et grafana en statut `Up`
- [ ] `http://localhost:3000` affiche la page de login Grafana (admin / admin)

---

## Statut

- [ ] Terminé
