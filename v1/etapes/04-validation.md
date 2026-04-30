# Étape 4 — Validation + rejected_trades

**Objectif :** rejeter les messages invalides et les tracer dans `rejected_trades`.

**Branche :** `feature/validation-rejected`

**Durée estimée :** 30 minutes

**Prérequis :** étape 3 terminée

---

## Modification à faire

`scripts/consumer.py` est modifié pour valider chaque message avant insertion.

---

## Règles de validation

Un message est rejeté si :

| Condition                        | Raison                  |
|----------------------------------|-------------------------|
| `price` <= 0                     | prix invalide           |
| `quantity` <= 0                  | quantité invalide       |
| `trade_id` manquant ou nul       | identifiant manquant    |
| `symbol` != `BTCUSDT`            | symbole inattendu       |
| champ obligatoire manquant       | payload malformé        |

---

## Logique dans le consumer

```
Pour chaque message Kafka :
  1. Désérialiser
  2. Valider
     → Si invalide : insérer dans rejected_trades + log WARNING + continuer
     → Si valide   : insérer dans trades + log INFO
```

---

## Requête rejected_trades

```sql
INSERT INTO rejected_trades (reason, raw_payload)
VALUES ($1, $2)
```

`raw_payload` est le JSON brut du message sous forme de string.

---

## Critère de validation

- Un message valide → insertion dans `trades`
- Un message avec `price = -1` → insertion dans `rejected_trades` avec la raison
- Le consumer ne plante pas sur un message invalide

Pour tester, tu peux publier manuellement un message invalide dans Kafka :

```bash
docker exec -it kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic crypto-trades
```

Puis taper :

```
{"trade_id": 99999, "symbol": "BTCUSDT", "price": "-1", "quantity": "0.001", "event_time": "2024-01-01T00:00:00+00:00", "trade_time": "2024-01-01T00:00:00+00:00", "is_buyer_maker": false}
```

Vérifier dans la base :

```bash
docker exec -it timescaledb psql -U user -d crypto \
  -c "SELECT * FROM rejected_trades;"
```

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/validation-rejected

# ... tu modifies scripts/consumer.py ...

git add scripts/consumer.py
git commit -m "feat: add message validation and rejected_trades"
git checkout develop
git merge feature/validation-rejected
```

---

## Statut

- [ ] Terminé
