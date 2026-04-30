# V1 — Roadmap et suivi

Objectif unique : un trade réel BTCUSDT visible dans TimescaleDB, avec API et dashboard Grafana.

---

## Progression

| Temps | Étape | Description                              | Branche Git                          | Statut  |
|-------|-------|------------------------------------------|--------------------------------------|---------|
| 1     | 0     | Environnement (git, .env, requirements)  | —                                    | à faire |
| 2     | 1     | Binance WebSocket → console              | feature/binance-websocket-console    | à faire |
| 2     | 2     | Kafka producer                           | feature/kafka-producer               | à faire |
| 2     | 3     | Kafka consumer → TimescaleDB             | feature/kafka-consumer-timescaledb   | à faire |
| 2     | 4     | Validation + rejected_trades             | feature/validation-rejected          | à faire |
| 3     | 5     | FastAPI /health /trades/latest           | feature/fastapi                      | à faire |
| 3     | 6     | Grafana dashboard                        | feature/grafana                      | à faire |
| 3     | 7     | README final + captures                  | feature/readme                       | à faire |

---

## Critère de fin de V1

```bash
docker compose -f docker-compose.dev.yml up -d
python scripts/producer.py
python scripts/consumer.py
```

→ Grafana affiche un graphe de prix BTC en temps réel avec des données réelles en base.

---

## Détail de chaque étape

- [Étape 0 — Environnement](etapes/00-environnement.md)
- [Étape 1 — Binance WebSocket console](etapes/01-binance-console.md)
- [Étape 2 — Kafka producer](etapes/02-kafka-producer.md)
- [Étape 3 — Kafka consumer + TimescaleDB](etapes/03-consumer-timescaledb.md)
- [Étape 4 — Validation + rejected_trades](etapes/04-validation.md)
- [Étape 5 — FastAPI](etapes/05-fastapi.md)
- [Étape 6 — Grafana](etapes/06-grafana.md)
- [Étape 7 — README final](etapes/07-readme.md)

---

## Règles pendant la V1

- Une étape à la fois. Ne pas commencer l'étape N+1 avant que l'étape N soit mergée.
- Une branche par étape. Toujours depuis `develop`.
- Les dossiers `src/domain/`, `src/ports/`, `src/adapters/` restent vides jusqu'au refactor (V2).
- Pas de `dependency-injector`. Les scripts sont procéduraux, c'est voulu.
- Si une idée surgit pendant le développement → la noter dans `docs/idees.md`, pas l'implémenter.
