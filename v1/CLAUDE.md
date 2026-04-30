# CLAUDE.md — V1 pipeline-streaming-crypto
Fichier de pilotage pour Claude pendant la phase V1.
Ce fichier prime sur le CLAUDE.md racine pour tout ce qui concerne le code V1.

---

## Contexte

Projet : pipeline streaming temps réel BTCUSDT.
Source : Binance Spot WebSocket Streams (flux public, pas d'auth).
Stack : Python 3.11+, aiokafka, asyncpg, FastAPI, TimescaleDB, Grafana, Docker Compose.

Le développeur est en transition data engineering. Il apprend en construisant.
Chaque étape doit être simple, lisible, et démontrable avant de passer à la suivante.

---

## Règle absolue

Le pipeline qui marche prime sur l'architecture propre.

Aucune abstraction (classe, port, adapter, service) ne doit être créée avant
qu'un flux réel fonctionne de bout en bout. Les dossiers `src/domain/`,
`src/ports/`, `src/adapters/`, `src/services/` existent mais restent vides
jusqu'au refactor V2.

---

## État actuel du projet

Mettre à jour cette section à chaque étape terminée.

| Étape | Description                        | Statut  |
|-------|------------------------------------|---------|
| 0     | Environnement (git, env, docker)   | ✅ fait  |
| 1     | Binance WebSocket → console        | ✅ fait  |
| 2     | Kafka producer                     | ✅ fait  |
| 3     | Kafka consumer → TimescaleDB       | ✅ fait  |
| 4     | Validation + rejected_trades       | ✅ fait  |
| 5     | FastAPI /health /trades/latest     | ✅ fait  |
| 6     | Grafana dashboard                  | à faire |
| 7     | README final                       | à faire |

---

## Fichiers existants à ne pas modifier

| Fichier                        | Raison                                      |
|-------------------------------|----------------------------------------------|
| CLAUDE.md (racine)            | Référence architecture globale               |
| v1/etapes/*.md                | Plan des étapes — modifier uniquement statut |
| db/migrations/001_init.sql    | DDL validé — ne pas changer le schéma        |
| apprentissage/                | Exercices indépendants — ne pas toucher      |

---

## Fichiers V1 — rôle et contenu attendu

### scripts/producer.py
Entrypoint du producer. Script procédural async.
Responsabilités :
- Connexion WebSocket Binance avec reconnexion automatique
- Parsing du payload brut → dict Python typé
- Publication dans Kafka (topic `crypto-trades`) via aiokafka
- Logs structurés via loguru

Ne pas y mettre : classes, ports, injection de dépendances, config pydantic-settings.
La config vient directement de `os.getenv()` en V1.

### scripts/consumer.py
Entrypoint du consumer. Script procédural async.
Responsabilités :
- Consommation du topic `crypto-trades` via aiokafka
- Désérialisation JSON → dict Python typé
- Validation des champs (prix, quantité, symbol, trade_id)
- Insertion dans `trades` via asyncpg (`ON CONFLICT DO NOTHING`)
- Rejet dans `rejected_trades` si validation échoue
- Logs structurés via loguru

Ne pas y mettre : classes, ports, injection de dépendances.

### src/api/app.py
Application FastAPI minimale.
Responsabilités :
- `GET /health` → état API + test connexion DB
- `GET /trades/latest?n=50` → derniers N trades
- `GET /trades/count` → nombre total de trades

Ne pas y mettre : routers séparés, services, dépendances injectées.
Tout dans un seul fichier en V1.

### infrastructure/config.py
Settings via pydantic-settings. Lit le fichier `.env`.
Instancié une fois, importé dans les scripts.

---

## Conventions V1

### Style Python
- Type hints sur toutes les fonctions publiques
- `loguru` pour tous les logs — jamais de `print()`
- `async/await` partout — pas de code synchrone bloquant
- Variables d'environnement via `infrastructure/config.py` — pas de `os.getenv()` direct dans les scripts

### Logs attendus
Format texte en développement (`LOG_FORMAT=text`) :

```
2024-01-01 14:23:01 | INFO | producer | [WS] Trade reçu : BTCUSDT #12345 @ 68432.12
2024-01-01 14:23:01 | INFO | producer | [KAFKA] Publié trade_id=12345
2024-01-01 14:23:01 | INFO | consumer | [DB] Inséré trade_id=12345
2024-01-01 14:23:01 | WARNING | consumer | [REJET] trade_id=99999 — raison: prix invalide (-1)
```

### Gestion des erreurs
Toujours logger avant de continuer ou relancer :

```python
# Pattern standard pour le consumer
try:
    await insert_trade(conn, trade)
    logger.info(f"[DB] Inséré trade_id={trade['trade_id']}")
except Exception as e:
    logger.error(f"[DB] Échec insertion : {e}")
    await insert_rejected(conn, str(e), raw_message)
```

---

## Mapping Binance → dict Python

Le payload brut Binance ne se propage jamais tel quel.
La fonction de parsing est dans `scripts/producer.py` et produit ce dict :

```python
{
    "event_time":     datetime,   # datetime.fromtimestamp(E/1000, tz=timezone.utc)
    "symbol":         str,        # raw["s"]
    "trade_id":       int,        # raw["t"]
    "price":          str,        # raw["p"] — gardé en str pour Kafka, Decimal à l'insertion
    "quantity":       str,        # raw["q"] — idem
    "trade_time":     datetime,   # datetime.fromtimestamp(T/1000, tz=timezone.utc)
    "is_buyer_maker": bool,       # raw["m"]
}
```

Note : `price` et `quantity` sont transmis en string dans Kafka pour préserver
la précision. Le consumer les convertit en `Decimal` juste avant l'insertion.

---

## Sérialisation Kafka

### Producer → Kafka
```python
import json
from datetime import datetime

def serialize(trade: dict) -> bytes:
    payload = {**trade}
    payload["event_time"] = trade["event_time"].isoformat()
    payload["trade_time"] = trade["trade_time"].isoformat()
    return json.dumps(payload).encode("utf-8")
```

### Kafka → Consumer
```python
from decimal import Decimal
from datetime import datetime

def deserialize(raw_bytes: bytes) -> dict:
    data = json.loads(raw_bytes.decode("utf-8"))
    data["event_time"] = datetime.fromisoformat(data["event_time"])
    data["trade_time"] = datetime.fromisoformat(data["trade_time"])
    data["price"]      = Decimal(data["price"])
    data["quantity"]   = Decimal(data["quantity"])
    return data
```

---

## Schéma SQL (référence)

```sql
-- trades
event_time      TIMESTAMPTZ    NOT NULL
symbol          TEXT           NOT NULL
trade_id        BIGINT         NOT NULL
price           NUMERIC(18, 8) NOT NULL
quantity        NUMERIC(18, 8) NOT NULL
trade_time      TIMESTAMPTZ    NOT NULL
is_buyer_maker  BOOLEAN
inserted_at     TIMESTAMPTZ    DEFAULT now()
PRIMARY KEY (symbol, trade_id, event_time)

-- rejected_trades
received_at  TIMESTAMPTZ  DEFAULT now()
reason       TEXT         NOT NULL
raw_payload  JSONB        NOT NULL
```

Insertion idempotente :
```sql
INSERT INTO trades (...) VALUES (...) ON CONFLICT (...) DO NOTHING
```

---

## Validation — règles V1

Rejeter si :
- `price` <= 0
- `quantity` <= 0
- `trade_id` est None ou 0
- `symbol` != valeur attendue (config `BINANCE_SYMBOL`)
- champ obligatoire manquant (KeyError)

Tout message rejeté → insertion dans `rejected_trades` avec la raison en clair
et le payload brut en JSONB.

---

## Reconnexion WebSocket

Pattern obligatoire dans `scripts/producer.py` :

```python
async def run():
    delay = 1
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                delay = 1  # reset au succès
                logger.info("[WS] Connecté")
                async for msg in ws:
                    await handle_message(msg)
        except Exception as e:
            logger.warning(f"[WS] Déconnecté : {e}. Reconnexion dans {delay}s")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
```

---

## Lancement V1

```bash
# Terminal 1 — infra
docker compose -f docker-compose.dev.yml up -d

# Terminal 2 — producer
python scripts/producer.py

# Terminal 3 — consumer
python scripts/consumer.py

# Terminal 4 — API (étape 5+)
uvicorn src.api.app:app --reload
```

---

## Ce que Claude ne doit PAS faire pendant la V1

- Créer des classes dans `scripts/producer.py` ou `scripts/consumer.py`
- Remplir les dossiers `src/domain/`, `src/ports/`, `src/adapters/`, `src/services/`
- Ajouter `dependency-injector`
- Créer des routers FastAPI séparés
- Ajouter Prometheus, alerting, multi-symboles
- Proposer des optimisations de performance avant que le flux de base tourne
- Réécrire une étape précédente avant que l'étape courante soit validée

---

## Ce que Claude DOIT faire pendant la V1

- Coder une étape à la fois, dans l'ordre défini
- Produire du code procédural lisible, commenté, sans sur-ingénierie
- Signaler si une étape semble trop complexe pour être faite en une session
- Mettre à jour le tableau de progression dans ce fichier après chaque étape
- Poser une question si le comportement attendu n'est pas clair plutôt que d'inventer
