# Exercice 01 — TimescaleDB

**Objectif :** lancer TimescaleDB via Docker, créer la table `trades`, insérer des données
manuellement, et faire des requêtes SQL simples.

**Durée estimée :** 30 à 45 minutes

**Prérequis :** Docker installé et fonctionnel (`docker --version` doit répondre)

---

## Contexte

TimescaleDB est une extension PostgreSQL optimisée pour les données temporelles.
Dans le projet, c'est là que tous les trades sont stockés.
Avant d'y insérer des vraies données depuis Kafka, tu dois savoir t'y connecter
et manipuler des données manuellement.

---

## Étape 1 — Lancer TimescaleDB

Lance un container TimescaleDB avec cette commande :

```bash
docker run -d \
  --name tsdb-exercice \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=crypto \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg15
```

Vérifie que le container tourne :

```bash
docker ps
```

Tu dois voir `tsdb-exercice` dans la liste avec le statut `Up`.

---

## Étape 2 — Se connecter

Connecte-toi à la base avec `psql` depuis l'intérieur du container :

```bash
docker exec -it tsdb-exercice psql -U user -d crypto
```

Tu dois voir le prompt `crypto=#`.

---

## Étape 3 — Activer l'extension TimescaleDB

Dans le prompt `psql`, tape :

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

---

## Étape 4 — Créer la table trades

```sql
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
```

Puis convertis-la en hypertable :

```sql
SELECT create_hypertable('trades', 'event_time');
```

---

## Étape 5 — Insérer des données manuellement

Insère trois trades fictifs :

```sql
INSERT INTO trades (event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker)
VALUES
  (now(), 'BTCUSDT', 1001, 68432.12000000, 0.00100000, now(), true),
  (now() - interval '5 seconds', 'BTCUSDT', 1002, 68430.50000000, 0.00250000, now() - interval '5 seconds', false),
  (now() - interval '10 seconds', 'BTCUSDT', 1003, 68435.00000000, 0.00050000, now() - interval '10 seconds', true);
```

---

## Étape 6 — Requêtes

Fais ces requêtes et observe les résultats.

Tous les trades :

```sql
SELECT * FROM trades ORDER BY event_time DESC;
```

Prix moyen :

```sql
SELECT AVG(price) AS prix_moyen FROM trades;
```

Nombre de trades :

```sql
SELECT COUNT(*) FROM trades;
```

Trades des 30 dernières secondes :

```sql
SELECT * FROM trades
WHERE event_time > now() - interval '30 seconds';
```

---

## Étape 7 — Tester l'idempotence

Essaie d'insérer un trade avec le même `trade_id` :

```sql
INSERT INTO trades (event_time, symbol, trade_id, price, quantity, trade_time, is_buyer_maker)
VALUES (now(), 'BTCUSDT', 1001, 99999.00000000, 1.00000000, now(), false)
ON CONFLICT (symbol, trade_id, event_time) DO NOTHING;
```

Vérifie que le prix n'a pas changé :

```sql
SELECT price FROM trades WHERE trade_id = 1001;
```

---

## Étape 8 — Nettoyer

Quand tu as terminé, arrête et supprime le container :

```bash
docker stop tsdb-exercice
docker rm tsdb-exercice
```

---

## Questions à te poser avant de regarder la correction

1. Qu'est-ce qu'une `hypertable` par rapport à une table normale ?
2. Pourquoi utilise-t-on `TIMESTAMPTZ` plutôt que `TIMESTAMP` ?
3. Que fait `ON CONFLICT DO NOTHING` exactement ?
4. Pourquoi `price` est en `NUMERIC` et pas en `FLOAT` ?

Note tes réponses. Elles seront comparées dans `corrections/01-timescaledb.md`.
