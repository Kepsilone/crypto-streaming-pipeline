# Étape 2 — Kafka producer

**Objectif :** envoyer chaque trade Binance dans le topic Kafka `crypto-trades`.

**Branche :** `feature/kafka-producer`

**Durée estimée :** 45 minutes

**Prérequis :** étape 1 terminée, Kafka tourne via docker-compose.dev.yml

---

## Modification à faire

`scripts/producer.py` est modifié pour publier dans Kafka après parsing.
Le code Binance WebSocket de l'étape 1 reste intact — on ajoute juste la publication.

---

## Ce que le script doit faire

1. Tout ce qu'il faisait à l'étape 1 (WebSocket + parsing)
2. Initialiser un `AIOKafkaProducer` au démarrage
3. Pour chaque trade parsé → sérialiser en JSON et publier dans `crypto-trades`
4. Afficher une confirmation dans le terminal : `[KAFKA] Envoyé trade_id=12345`

---

## Format du message Kafka

Le message publié dans Kafka est un JSON avec les champs suivants :

```json
{
  "event_time": "2024-01-01T14:23:01.123000+00:00",
  "symbol": "BTCUSDT",
  "trade_id": 12345,
  "price": "68432.12000000",
  "quantity": "0.00100000",
  "trade_time": "2024-01-01T14:23:01.123000+00:00",
  "is_buyer_maker": true
}
```

Note : `price` et `quantity` sont sérialisés en string pour préserver la précision Decimal.
Le consumer les reconvertira en Decimal avant insertion.

---

## Vérifier que les messages arrivent dans Kafka

Depuis un second terminal, lance un consumer de test :

```bash
docker exec -it kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic crypto-trades \
  --from-beginning
```

Tu dois voir les messages JSON défiler.

---

## Critère de validation

- Le producer tourne sans erreur
- Le consumer de test Kafka affiche des messages JSON en temps réel
- Chaque message contient bien tous les champs

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/kafka-producer

# ... tu modifies scripts/producer.py ...

git add scripts/producer.py
git commit -m "feat: publish binance trades to kafka topic"
git checkout develop
git merge feature/kafka-producer
```

---

## Statut

- [ ] Terminé
