# Pipeline de Streaming Temps Réel
## Architecture, Concepts et Implémentation

*Rapport académique — Projet BTCUSDT avec Kafka, TimescaleDB, FastAPI et Grafana*

**Auteur :** Sabeur Jedid  
**Date :** Avril 2026  
**Contexte :** Transition Data Engineering — V1

---

## Résumé exécutif

Ce rapport présente la conception et l'implémentation d'un pipeline de données temps réel complet, utilisant les données publiques de trading BTCUSDT de la plateforme Binance comme source. L'objectif pédagogique est de démontrer une architecture événementielle (event-driven) représentative des pratiques professionnelles en data engineering, transposable à tout domaine produisant des données horodatées à haute fréquence : capteurs industriels, logs machine, monitoring IoT ou supervision de production.

Le pipeline implémente cinq briques fondamentales : ingestion WebSocket temps réel, découplage par message broker (Apache Kafka), validation et rejet contrôlé des données invalides, stockage time-series optimisé (TimescaleDB), exposition via API REST (FastAPI) et visualisation en temps réel (Grafana). L'ensemble est orchestré localement via Docker Compose, sans dépendance cloud.

---

## Table des matières

1. [Contexte et objectifs](#1-contexte-et-objectifs)
2. [Vue d'ensemble de l'architecture](#2-vue-densemble-de-larchitecture)
3. [Brique 1 — Ingestion WebSocket (producer.py)](#3-brique-1--ingestion-websocket-producerpy)
4. [Brique 2 — Apache Kafka : le découpleur](#4-brique-2--apache-kafka--le-découpleur)
5. [Brique 3 — Traitement et validation (consumer.py)](#5-brique-3--traitement-et-validation-consumerpy)
6. [Brique 4 — TimescaleDB : stockage time-series](#6-brique-4--timescaledb--stockage-time-series)
7. [Brique 5 — FastAPI : exposition REST](#7-brique-5--fastapi--exposition-rest)
8. [Brique 6 — Grafana : visualisation as-code](#8-brique-6--grafana--visualisation-as-code)
9. [Concepts transversaux](#9-concepts-transversaux)
10. [Limites connues et perspectives V2](#10-limites-connues-et-perspectives-v2)
11. [Conclusion](#11-conclusion)

---

## 1. Contexte et objectifs

### 1.1 Pourquoi les données crypto ?

Binance met à disposition un flux WebSocket public, gratuit, sans authentification, émettant des événements de trading à une fréquence de 2 à 10 messages par seconde. Ce flux constitue une source idéale pour un projet pédagogique : données réelles, structurées, continues, et représentatives de ce que l'on rencontre en industrie (télémétrie machine, compteurs d'énergie, capteurs process).

**Important :** ce projet ne vise pas la finance. Le domaine crypto n'est qu'un prétexte technique. Toute l'architecture est réutilisable pour des données industrielles ou opérationnelles. Un ingénieur data junior doit savoir l'expliquer ainsi.

### 1.2 Objectifs pédagogiques

- Maîtriser le flux complet d'un pipeline streaming : source → broker → traitement → stockage → visualisation.
- Comprendre le rôle de chaque composant et les justifications de leur présence.
- Implémenter une validation de données avec circuit de rejet traçable.
- Appliquer les patterns professionnels : idempotence, désérialisation typée, gestion des erreurs, logs structurés.
- Pratiquer l'infrastructure as-code : Docker Compose, provisioning Grafana, migrations SQL automatiques.

---

## 2. Vue d'ensemble de l'architecture

L'architecture suit un patron événementiel (event-driven architecture) à flux unidirectionnel. Les données transitent d'une source externe vers un stockage persistant, en passant par un broker de messages qui isole chaque étape du reste du pipeline.

### 2.1 Flux de données schématisé

```
Binance WebSocket (flux public)
        │
        │  Message JSON brut : {"e":"trade","s":"BTCUSDT","p":"76295.42","q":"0.001",...}
        ▼
┌─────────────────────────────┐
│      scripts/producer.py    │  ← Python asyncio + websockets
│  - Connexion WebSocket       │
│  - Parsing : champs bruts   │
│    → dict Python typé       │
│  - Sérialisation JSON       │
│  - Publication Kafka        │
└─────────────┬───────────────┘
              │  Topic "crypto-trades"
              ▼
┌─────────────────────────────┐
│      Apache Kafka 3.7       │  ← KRaft, pas de Zookeeper
│  Broker de messages         │
│  Persistance temporaire     │
│  Découplage prod/conso      │
└─────────────┬───────────────┘
              │  Consumer group "crypto-consumer-group"
              ▼
┌─────────────────────────────┐
│      scripts/consumer.py    │  ← Python asyncio + aiokafka
│  - Désérialisation JSON     │
│  - Validation métier        │
│    ├─ Trade valide ──────────────► TABLE trades
│    └─ Trade invalide ───────────► TABLE rejected_trades
└─────────────────────────────┘
              │
              ▼
┌─────────────────────────────┐
│        TimescaleDB          │  ← PostgreSQL 15 + extension timescaledb
│  Hypertable partitionnée    │
│  par event_time             │
└──────────┬──────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
FastAPI         Grafana
(API REST)      (Dashboard temps réel)
```

### 2.2 Composants et rôles

| Composant | Rôle | Technologie |
|-----------|------|-------------|
| producer.py | Ingestion WebSocket → publication Kafka | Python asyncio, websockets, aiokafka |
| Kafka | Découplage, tampon de messages, replay possible | Apache Kafka 3.7, KRaft |
| consumer.py | Lecture Kafka, validation, insertion DB | Python asyncio, aiokafka, asyncpg |
| TimescaleDB | Stockage time-series optimisé | PostgreSQL 15 + extension timescaledb |
| FastAPI | API REST pour consommation programmatique | FastAPI, asyncpg, uvicorn |
| Grafana | Dashboard temps réel, provisionné as-code | Grafana (image Docker) |
| Docker Compose | Orchestration locale de l'infrastructure | Docker, YAML |

---

## 3. Brique 1 — Ingestion WebSocket (producer.py)

### 3.1 Qu'est-ce qu'un WebSocket ?

Le protocole HTTP classique fonctionne en mode requête-réponse : le client demande, le serveur répond, la connexion se ferme. Pour des données temps réel, ce modèle est inefficace (polling permanent, latence, charge serveur).

Le WebSocket (RFC 6455) établit une connexion persistante bidirectionnelle. Une fois ouverte, le serveur peut envoyer des messages au client à tout moment, sans que le client ait besoin de les redemander. Binance utilise ce protocole pour pousser chaque trade en temps réel, dès qu'il se produit sur le marché.

### 3.2 Le flux Binance @trade

Chaque message reçu a la structure suivante :

```json
{
  "e": "trade",          // type d'événement
  "E": 1714492014569,    // timestamp événement (millisecondes Unix UTC)
  "s": "BTCUSDT",        // symbole
  "t": 3891234567,       // trade_id (identifiant unique du trade)
  "p": "76295.42000000", // prix (string pour préserver la précision)
  "q": "0.00100000",     // quantité (string)
  "T": 1714492014561,    // timestamp du trade (millisecondes Unix UTC)
  "m": false             // true si l'acheteur est le maker
}
```

**Attention critique :** les prix et quantités sont transmis en string par Binance, jamais en nombre flottant. C'est intentionnel : les flottants IEEE 754 introduisent des erreurs d'arrondi (ex: 0.1 + 0.2 = 0.30000000000000004). En finance et data engineering, on utilise le type `Decimal` pour toute valeur monétaire.

### 3.3 Parsing et typage

Le payload brut Binance est immédiatement converti en dict Python typé. Ce mapping est la seule couche qui connaît le format Binance :

```python
def parse_trade(raw: dict) -> dict:
    return {
        "event_time":     datetime.fromtimestamp(raw["E"] / 1000, tz=timezone.utc),
        "symbol":         raw["s"],
        "trade_id":       int(raw["t"]),
        "price":          Decimal(raw["p"]),   # string → Decimal
        "quantity":       Decimal(raw["q"]),   # string → Decimal
        "trade_time":     datetime.fromtimestamp(raw["T"] / 1000, tz=timezone.utc),
        "is_buyer_maker": bool(raw["m"]),
    }
```

Les timestamps Binance sont en millisecondes Unix. La division par 1000 et la conversion avec `timezone.utc` garantissent des objets datetime "aware" (avec fuseau horaire). L'utilisation de `datetime.utcnow()` est dépréciée depuis Python 3.12 — `datetime.now(timezone.utc)` est la forme correcte.

### 3.4 Reconnexion automatique avec backoff exponentiel

Une connexion WebSocket peut se fermer pour de nombreuses raisons : instabilité réseau, timeout côté serveur, redémarrage Binance. Un pipeline de production doit se reconnecter automatiquement. Le pattern utilisé est le backoff exponentiel : on attend de plus en plus longtemps entre les tentatives pour ne pas saturer le serveur en cas de panne prolongée.

```python
delay = 1
while True:
    try:
        async with websockets.connect(WS_URL) as ws:
            delay = 1  # reset si connexion réussie
            async for msg in ws:
                await handle_message(msg, producer)
    except Exception as e:
        logger.warning(f"Déconnexion : {e}. Reconnexion dans {delay}s")
    await asyncio.sleep(delay)
    delay = min(delay * 2, 60)  # 1s → 2s → 4s → 8s → ... → 60s max
```

---

## 4. Brique 2 — Apache Kafka : le découpleur

### 4.1 Le problème que Kafka résout

Sans Kafka, le producer écrirait directement dans TimescaleDB. Cette approche a plusieurs problèmes :

- Si TimescaleDB est lent ou indisponible, les trades sont perdus (le WebSocket ne les stocke pas).
- Le producer et le consumer sont fortement couplés : un ralentissement de l'un bloque l'autre.
- Impossible d'ajouter un deuxième consommateur (ex: alerting) sans modifier le producer.
- Pas de replay possible en cas d'erreur de traitement.

Kafka résout ces problèmes en servant de tampon persistant entre la production et la consommation des messages.

### 4.2 Concepts fondamentaux de Kafka

| Concept | Définition simple | Dans ce projet |
|---------|-------------------|----------------|
| Topic | File de messages nommée | crypto-trades |
| Producer | Processus qui écrit dans un topic | scripts/producer.py |
| Consumer | Processus qui lit depuis un topic | scripts/consumer.py |
| Consumer group | Groupe de consumers partageant le travail | crypto-consumer-group |
| Offset | Position d'un message dans une partition | Suivi automatique |
| Partition | Sous-division du topic pour la parallélisation | 1 partition (dev) |
| Broker | Serveur Kafka qui stocke les messages | Container Kafka 3.7 |

### 4.3 KRaft : Kafka sans Zookeeper

Historiquement, Kafka nécessitait Zookeeper pour gérer les métadonnées du cluster (élection du leader, configuration des topics). Depuis Kafka 2.8, le mode KRaft (Kafka Raft) permet à Kafka de gérer lui-même ses métadonnées sans Zookeeper. Ce projet utilise Kafka 3.7 en mode KRaft pur : un seul container, pas de Zookeeper, configuration plus simple et plus moderne.

### 4.4 Sérialisation JSON pour Kafka

Kafka transporte des bytes bruts, sans schéma imposé. Le choix de JSON est pragmatique en V1 : lisible, déboguable facilement. Les dates sont sérialisées en ISO 8601 (chaîne de caractères) et les Decimals en string pour préserver la précision :

```python
def serialize(trade: dict) -> bytes:
    payload = {
        "event_time":     trade["event_time"].isoformat(),  # datetime → str ISO 8601
        "symbol":         trade["symbol"],
        "trade_id":       trade["trade_id"],
        "price":          str(trade["price"]),   # Decimal → str
        "quantity":       str(trade["quantity"]), # Decimal → str
        "trade_time":     trade["trade_time"].isoformat(),
        "is_buyer_maker": trade["is_buyer_maker"],
    }
    return json.dumps(payload).encode("utf-8")
```

**Note :** en production, on utiliserait Avro ou Protobuf avec un Schema Registry pour valider le format des messages à la source. C'est une limite connue de la V1.

---

## 5. Brique 3 — Traitement et validation (consumer.py)

### 5.1 Désérialisation : l'opération inverse du producer

Le consumer lit des bytes depuis Kafka et doit reconstituer un dict Python typé. C'est l'opération symétrique de la sérialisation du producer :

```python
def deserialize(raw_bytes: bytes) -> dict:
    data = json.loads(raw_bytes.decode("utf-8"))
    data["event_time"] = datetime.fromisoformat(data["event_time"])  # str → datetime
    data["trade_time"] = datetime.fromisoformat(data["trade_time"])
    data["price"]      = Decimal(data["price"])     # str → Decimal
    data["quantity"]   = Decimal(data["quantity"])
    return data
```

### 5.2 Validation métier

Avant d'insérer un trade en base, le consumer valide qu'il respecte les règles métier. La validation lève une `ValueError` avec un message clair si une règle est violée :

```python
def validate_trade(trade: dict) -> None:
    if not trade.get("trade_id"):
        raise ValueError("trade_id manquant ou nul")
    if trade["price"] <= 0:
        raise ValueError(f"prix invalide : {trade['price']}")
    if trade["quantity"] <= 0:
        raise ValueError(f"quantité invalide : {trade['quantity']}")
    if trade["symbol"].upper() != EXPECTED_SYMBOL:
        raise ValueError(f"symbole inattendu : {trade['symbol']}")
```

Ces règles semblent évidentes, mais elles sont essentielles. Des données corrompues ou mal formatées peuvent provenir d'un bug upstream, d'un test, ou d'une injection malveillante. Valider explicitement chaque champ critique est une pratique obligatoire en data engineering.

### 5.3 Circuit de rejet : rejected_trades

Un trade invalide n'est pas silencieusement ignoré. Il est inséré dans la table `rejected_trades` avec sa raison de rejet et son payload brut en JSONB. Ce circuit de rejet permet :

- D'auditer a posteriori les données invalides.
- De comprendre l'origine d'un problème (bug producer, test, données corrompues).
- De rejouer les messages corrigés si nécessaire.

```python
async for msg in consumer:
    raw_data = {}
    try:
        raw_data = json.loads(msg.value.decode("utf-8"))
        trade = deserialize(msg.value)
        validate_trade(trade)
        await insert_trade(conn, trade)
        logger.info(f"[DB] Inséré trade_id={trade['trade_id']}")

    except ValueError as e:
        # Trade invalide → circuit de rejet
        logger.warning(f"[REJET] offset={msg.offset} — {e}")
        await insert_rejected(conn, str(e), raw_data)

    except Exception as e:
        # Erreur technique : log et continue — le pipeline ne s'arrête pas
        logger.error(f"[DB] Erreur inattendue offset={msg.offset} : {e}")
```

### 5.4 Idempotence : ON CONFLICT DO NOTHING

Lors d'un redémarrage du consumer, Kafka peut réémettre des messages déjà traités (en fonction de l'offset commité). Sans protection, ces messages créeraient des doublons en base.

La clause `ON CONFLICT DO NOTHING` dans la requête d'insertion résout ce problème : si un trade avec la même clé primaire `(symbol, trade_id, event_time)` existe déjà, l'insertion est silencieusement ignorée. Le consumer est ainsi **idempotent** : exécuter la même opération plusieurs fois donne le même résultat qu'une seule fois.

```sql
INSERT INTO trades (event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (symbol, trade_id, event_time) DO NOTHING
```

---

## 6. Brique 4 — TimescaleDB : stockage time-series

### 6.1 Pourquoi pas un PostgreSQL standard ?

TimescaleDB est une extension PostgreSQL, pas un remplacement. On continue d'utiliser du SQL standard, les mêmes outils, la même syntaxe. L'extension ajoute des optimisations spécifiques aux données temporelles :

| Critère | PostgreSQL standard | TimescaleDB |
|---------|---------------------|-------------|
| Requêtes par interval de temps | Scan séquentiel si pas d'index | Partition automatique → scan limité |
| Insertion haute fréquence | Dégradation avec le volume | Conçu pour ingestion continue |
| Agrégations temporelles | SQL standard | Fonctions `time_bucket()` natives |
| Rétention des données | Manuelle | Policies automatiques (V2+) |
| Compatibilité SQL | Complète | Complète (c'est du PostgreSQL) |

### 6.2 La hypertable : partitionnement automatique

Le concept central de TimescaleDB est la **hypertable**. Une hypertable est une table PostgreSQL normale qui est automatiquement partitionnée par intervalles de temps (chunks). Chaque chunk correspond à une fenêtre temporelle (par défaut 7 jours).

Lorsqu'on interroge un interval de temps (ex: "les trades des 15 dernières minutes"), TimescaleDB ne scanne que les chunks qui couvrent cet interval, au lieu de parcourir toute la table. Sur des millions de lignes, le gain de performance est considérable.

```sql
-- Création de la table normale
CREATE TABLE trades (
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

-- Conversion en hypertable (partitionnement par event_time)
SELECT create_hypertable('trades', 'event_time', if_not_exists => TRUE);
```

### 6.3 Contrainte sur la clé primaire

TimescaleDB impose une contrainte importante : toute contrainte d'unicité (et donc toute clé primaire) sur une hypertable doit inclure la colonne de partitionnement (ici `event_time`). C'est pourquoi la clé primaire est `(symbol, trade_id, event_time)` et non simplement `(symbol, trade_id)`.

**Identifiant métier vs clé technique :** le vrai identifiant d'un trade Binance est `(symbol, trade_id)`. L'`event_time` est ajouté pour satisfaire TimescaleDB, pas pour des raisons métier.

### 6.4 NUMERIC(18,8) : précision décimale

Le type `NUMERIC(18,8)` stocke des nombres avec 18 chiffres significatifs dont 8 après la virgule. Contrairement au type `FLOAT` (virgule flottante binaire), `NUMERIC` est exact. Pour des montants financiers, cette précision est obligatoire. La chaîne `"76295.42000000"` retournée par Binance est stockée et restituée exactement.

---

## 7. Brique 5 — FastAPI : exposition REST

### 7.1 Rôle de l'API dans ce pipeline

Grafana lit TimescaleDB directement via le plugin PostgreSQL. FastAPI n'est donc pas nécessaire pour la visualisation. Son rôle est de rendre les données accessibles programmatiquement : applications externes, scripts d'analyse, tests d'intégration, monitoring de l'état du pipeline.

### 7.2 Les trois endpoints

| Endpoint | Méthode | Description | Cas d'usage |
|----------|---------|-------------|-------------|
| `/health` | GET | État de l'API + connexion DB + count total | Monitoring, healthcheck |
| `/trades/latest` | GET | Derniers N trades (défaut 50, max 500) | Consommation applicative |
| `/trades/count` | GET | Nombre total de trades en base | Métriques, tests |

### 7.3 Pool de connexions et lifespan

Une erreur fréquente est d'ouvrir une connexion base de données à chaque requête HTTP. C'est coûteux (handshake TCP, authentification) et ne passe pas à l'échelle. Le pattern correct est le **pool de connexions** : un ensemble de connexions ouvertes au démarrage de l'application, réutilisées pour chaque requête.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(TIMESCALEDB_URL, min_size=1, max_size=5)
    yield  # l'application tourne ici
    await _pool.close()  # fermeture propre à l'arrêt
```

Le gestionnaire `lifespan` (introduit dans FastAPI 0.93) remplace les anciens événements `on_event("startup")` et `on_event("shutdown")`, désormais dépréciés.

---

## 8. Brique 6 — Grafana : visualisation as-code

### 8.1 Grafana lit TimescaleDB directement

Grafana inclut un plugin natif pour PostgreSQL. Puisque TimescaleDB est du PostgreSQL avec des extensions, Grafana s'y connecte nativement. Les requêtes SQL des panels utilisent les fonctions TimescaleDB comme `time_bucket()` pour agréger les données par fenêtre temporelle.

```sql
-- Requête du panel "Prix BTCUSDT — moyenne 5s"
SELECT
  time_bucket('5 seconds', event_time) AS time,
  AVG(price::float8) AS "prix moyen (5s)"
FROM trades
WHERE $__timeFilter(event_time)   -- macro Grafana : remplace par la plage sélectionnée
GROUP BY time
ORDER BY time
```

### 8.2 Provisioning as-code

Par défaut, Grafana stocke sa configuration dans une base SQLite interne. Si le container est recréé, toute la configuration est perdue. Le **provisioning** résout ce problème : la datasource et le dashboard sont définis dans des fichiers YAML/JSON montés dans le container au démarrage. Grafana les charge automatiquement.

| Fichier | Rôle |
|---------|------|
| `grafana/provisioning/datasources/timescaledb.yaml` | Définit la connexion TimescaleDB (URL, user, password, UID) |
| `grafana/provisioning/dashboards/dashboard.yaml` | Indique à Grafana où trouver les fichiers JSON de dashboards |
| `grafana/provisioning/dashboards/crypto-trades.json` | Définition complète du dashboard (panels, requêtes SQL, refresh) |

Cette approche est appelée "infrastructure as-code" : la configuration est versionnée dans Git, reproductible sur n'importe quelle machine, et ne dépend pas d'un état interne de l'application.

---

## 9. Concepts transversaux

### 9.1 Programmation asynchrone avec asyncio

Tout le code Python de ce projet utilise `async/await`. C'est essentiel pour un pipeline I/O-bound (qui passe son temps à attendre des données réseau ou DB).

En Python synchrone, une attente de réponse réseau bloque tout le programme. Avec asyncio, pendant qu'on attend une réponse de Kafka, Python peut traiter autre chose (logs, autres connexions). Un seul thread gère des centaines d'opérations concurrentes.

### 9.2 Logs structurés avec loguru

Les logs sont la première ligne de débogage d'un pipeline de production. `loguru` fournit des logs formatés, avec niveau (INFO, WARNING, ERROR), horodatage automatique, et configuration simple. On n'utilise jamais `print()` dans les modules de production.

```python
# Bonne pratique
logger.info(f"[DB] Inséré trade_id={trade['trade_id']} | prix={trade['price']:.2f}")
logger.warning(f"[REJET] offset={msg.offset} — prix invalide : {trade['price']}")
logger.error(f"[DB] Erreur inattendue : {e}")

# À ne jamais faire dans un module de production
print(f"trade inséré : {trade['trade_id']}")  # PAS DE PRINT
```

### 9.3 Variables d'environnement et .env

Aucune valeur de configuration (URL de base de données, credentials, noms de topics) n'est codée en dur dans le code source. Toutes ces valeurs proviennent du fichier `.env` chargé au démarrage via `python-dotenv`. Ce fichier n'est jamais versionné (il est dans `.gitignore`). Un `.env.example` documente les variables attendues.

### 9.4 Docker Compose et infrastructure locale

Docker Compose orchestre trois services : Kafka, TimescaleDB et Grafana. Chaque service est un container isolé. Les migrations SQL (`001_init.sql`) sont montées dans `/docker-entrypoint-initdb.d/` de TimescaleDB et exécutées automatiquement au premier démarrage. Le provisioning Grafana est monté dans `/etc/grafana/provisioning/`.

### 9.5 Asyncpg vs psycopg2

`psycopg2` est le driver PostgreSQL historique pour Python, mais il est synchrone : chaque requête bloque le thread. `asyncpg` est un driver entièrement asynchrone, écrit en C, optimisé pour les connexions à haute fréquence. Il est le choix standard pour tout code Python asyncio qui accède à PostgreSQL.

---

## 10. Limites connues et perspectives V2

### 10.1 Limites de la V1

| Limite | Explication | Solution V2 |
|--------|-------------|-------------|
| JSON sans schéma | Pas de validation du format des messages dans Kafka | Avro + Schema Registry |
| Exactly-once partiel | L'idempotence est côté base, pas de transaction distribuée | Kafka transactions + outbox pattern |
| Mono-symbole | Seul BTCUSDT est traité | Configuration multi-symboles |
| Pas de tests | Aucun test unitaire ou d'intégration | pytest + testcontainers |
| Architecture procédurale | Scripts sans séparation des responsabilités | Hexagonal Architecture (Ports & Adapters) |
| Pas de métriques | Pas de Prometheus / alerting | Prometheus + Grafana Alerting |

### 10.2 Architecture hexagonale V2

La V2 prévoit un refactor vers l'architecture hexagonale (Ports & Adapters). Cette architecture sépare le code en trois zones :

- **Domaine :** entités et règles métier pures (`Trade`, règles de validation). Sans dépendance vers Kafka ou PostgreSQL.
- **Ports :** interfaces (abstractions) définissant comment le domaine communique avec l'extérieur (`MessageProducerPort`, `TradeRepositoryPort`).
- **Adapters :** implémentations concrètes des ports (`BinanceWebSocketAdapter`, `KafkaProducerAdapter`, `TimescaleDBRepository`).

Cette séparation permet de tester le domaine sans infrastructure (tests unitaires rapides), et de remplacer un adapter par un autre (ex: remplacer Kafka par RabbitMQ) sans toucher au domaine ni aux autres adapters.

---

## 11. Conclusion

Ce projet implémente un pipeline de données temps réel complet, du flux brut à la visualisation, en passant par le découplage, la validation et le stockage. Les choix techniques (Kafka KRaft, TimescaleDB, asyncpg, FastAPI, Grafana) sont cohérents avec les pratiques professionnelles en data engineering.

La valeur pédagogique principale n'est pas dans la technologie crypto, mais dans la maîtrise de l'enchaînement : comment une donnée brute devient une information visualisable, avec validation, traçabilité des rejets, idempotence et reproductibilité (Docker, provisioning as-code).

Ce pipeline, avec de légères modifications, pourrait ingérer des mesures de capteurs industriels (température, pression, débit), des logs de machines-outils, des données de consommation énergétique ou tout autre flux horodaté à haute fréquence. C'est cette généricité qui en fait un projet de portfolio crédible pour une transition vers le data engineering.

---

*— Fin du rapport —*
