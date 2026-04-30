# Exercice 02 — Kafka

**Objectif :** lancer Kafka via Docker, créer un topic, publier un message depuis Python,
le consommer depuis Python.

**Durée estimée :** 45 à 60 minutes

**Prérequis :** exercice 01 terminé, Python 3.11+ installé

---

## Contexte

Dans le projet, Kafka joue le rôle de tampon entre le producer (Binance WebSocket)
et le consumer (TimescaleDB). Si le consumer tombe, les messages s'accumulent dans Kafka
et sont traités dès qu'il redémarre — aucune donnée n'est perdue.

Avant d'intégrer Kafka dans le pipeline, tu dois comprendre ce qu'est un topic,
comment un producer publie, et comment un consumer lit.

---

## Étape 1 — Lancer Kafka (mode KRaft, sans Zookeeper)

Crée un fichier `docker-compose-kafka.yml` dans un dossier temporaire :

```yaml
services:
  kafka:
    image: apache/kafka:3.7.0
    container_name: kafka-exercice
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka-exercice:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
    ports:
      - "9092:9092"
```

Lance Kafka :

```bash
docker compose -f docker-compose-kafka.yml up -d
```

Vérifie que Kafka tourne :

```bash
docker ps
```

---

## Étape 2 — Créer un topic

Entre dans le container et crée un topic `crypto-trades` :

```bash
docker exec -it kafka-exercice /opt/kafka/bin/kafka-topics.sh \
  --create \
  --topic crypto-trades \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
```

Vérifie que le topic existe :

```bash
docker exec -it kafka-exercice /opt/kafka/bin/kafka-topics.sh \
  --list \
  --bootstrap-server localhost:9092
```

---

## Étape 3 — Installer aiokafka

Dans ton environnement Python :

```bash
pip install aiokafka
```

---

## Étape 4 — Écrire un producer simple

Crée un fichier `producer_test.py` :

```python
import asyncio
import json
from aiokafka import AIOKafkaProducer


async def main():
    producer = AIOKafkaProducer(
        bootstrap_servers="localhost:9092"
    )
    await producer.start()

    try:
        for i in range(5):
            message = {
                "trade_id": i + 1,
                "symbol": "BTCUSDT",
                "price": "68432.12000000",
                "quantity": "0.00100000",
            }
            value = json.dumps(message).encode("utf-8")
            await producer.send_and_wait("crypto-trades", value)
            print(f"Envoyé : {message}")

    finally:
        await producer.stop()


asyncio.run(main())
```

Lance-le :

```bash
python producer_test.py
```

---

## Étape 5 — Écrire un consumer simple

Crée un fichier `consumer_test.py` :

```python
import asyncio
import json
from aiokafka import AIOKafkaConsumer


async def main():
    consumer = AIOKafkaConsumer(
        "crypto-trades",
        bootstrap_servers="localhost:9092",
        group_id="test-group",
        auto_offset_reset="earliest",  # lire depuis le début
    )
    await consumer.start()

    try:
        print("En attente de messages... (Ctrl+C pour arrêter)")
        async for msg in consumer:
            data = json.loads(msg.value.decode("utf-8"))
            print(f"Reçu [offset {msg.offset}] : {data}")

    except KeyboardInterrupt:
        pass
    finally:
        await consumer.stop()


asyncio.run(main())
```

Lance-le dans un second terminal :

```bash
python consumer_test.py
```

Tu dois voir les 5 messages que le producer a envoyés.

---

## Étape 6 — Tester la persistance

Arrête le consumer (Ctrl+C).
Relance le producer pour envoyer 5 nouveaux messages.
Relance le consumer.

**Question :** combien de messages vois-tu ? Pourquoi ?

---

## Étape 7 — Tester la reprise d'offset

Arrête le consumer.
Relance-le avec `auto_offset_reset="latest"` au lieu de `"earliest"`.
Envoie de nouveaux messages avec le producer.

**Question :** quelle est la différence entre `earliest` et `latest` ?

---

## Étape 8 — Nettoyer

```bash
docker compose -f docker-compose-kafka.yml down
```

---

## Questions à te poser avant de regarder la correction

1. Qu'est-ce qu'un topic Kafka ? Quelle analogie avec un système de fichiers ou une queue ?
2. Pourquoi le consumer peut-il relire des messages anciens avec `earliest` ?
3. Qu'est-ce qu'un `group_id` ? À quoi ça sert ?
4. Pourquoi encode-t-on le message en `utf-8` avant de l'envoyer ?
5. Quelle est la différence entre `send()` et `send_and_wait()` ?

Note tes réponses. Elles seront comparées dans `corrections/02-kafka.md`.
