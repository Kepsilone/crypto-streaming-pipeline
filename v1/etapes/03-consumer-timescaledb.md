# Étape 3 — Kafka consumer + TimescaleDB

**Objectif :** lire les messages Kafka et les insérer dans TimescaleDB.

**Branche :** `feature/kafka-consumer-timescaledb`

**Durée estimée :** 60 minutes

**Prérequis :** étape 2 terminée, TimescaleDB tourne via docker-compose.dev.yml

---

## Fichier à créer

```
scripts/consumer.py
```

---

## Initialisation de la base

Le `docker-compose.dev.yml` monte automatiquement `db/migrations/` dans le container
TimescaleDB via `docker-entrypoint-initdb.d`. Le fichier `001_init.sql` est donc
exécuté au premier démarrage.

Si TimescaleDB tourne déjà et que la table n'existe pas, tu peux l'initialiser manuellement :

```bash
docker exec -it timescaledb psql -U user -d crypto \
  -f /docker-entrypoint-initdb.d/001_init.sql
```

Vérifie que la table existe :

```bash
docker exec -it timescaledb psql -U user -d crypto -c "\dt"
```

---

## Ce que le script doit faire

1. Initialiser un `AIOKafkaConsumer` sur le topic `crypto-trades`
2. Initialiser une connexion `asyncpg` vers TimescaleDB
3. Pour chaque message Kafka :
   - Désérialiser le JSON
   - Convertir `price` et `quantity` en `Decimal`
   - Convertir `event_time` et `trade_time` en `datetime UTC`
   - Insérer dans `trades` avec `ON CONFLICT DO NOTHING`
   - Afficher : `[DB] Inséré trade_id=12345`

---

## Requête d'insertion

```sql
INSERT INTO trades (event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (symbol, trade_id, event_time) DO NOTHING
```

Avec `asyncpg`, l'exécution ressemble à :

```python
await conn.execute(
    "INSERT INTO trades ... ON CONFLICT ... DO NOTHING",
    event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker
)
```

---

## Vérifier que les données arrivent en base

```bash
docker exec -it timescaledb psql -U user -d crypto \
  -c "SELECT trade_id, price, quantity, event_time FROM trades ORDER BY event_time DESC LIMIT 5;"
```

---

## Critère de validation

- Le consumer tourne sans erreur
- La table `trades` contient des lignes réelles
- Relancer le consumer ne crée pas de doublons (idempotence via `ON CONFLICT`)

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/kafka-consumer-timescaledb

# ... tu codes scripts/consumer.py ...

git add scripts/consumer.py db/migrations/001_init.sql
git commit -m "feat: consume kafka trades and insert into timescaledb"
git checkout develop
git merge feature/kafka-consumer-timescaledb
```

---

## Statut

- [ ] Terminé
