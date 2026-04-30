# Exercice 03 — Binance WebSocket

**Objectif :** se connecter au WebSocket public Binance, recevoir des trades BTCUSDT
en temps réel, parser le payload, et afficher les données proprement en console.

**Durée estimée :** 30 à 45 minutes

**Prérequis :** exercices 01 et 02 terminés, Python 3.11+ installé

---

## Contexte

Le WebSocket Binance est la source de données du projet.
Binance pousse en temps réel chaque trade exécuté sur la paire BTCUSDT.
Avant de connecter cette source à Kafka, tu dois comprendre le format des données
et savoir les parser correctement.

Aucune authentification requise. C'est un flux public gratuit.

---

## Étape 1 — Installer websockets

```bash
pip install websockets
```

---

## Étape 2 — Lire les données brutes

Crée un fichier `binance_raw.py` :

```python
import asyncio
import json
import websockets


BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"


async def main():
    async with websockets.connect(BINANCE_WS_URL) as ws:
        print("Connecté. En attente de trades...\n")
        for _ in range(5):  # lire seulement 5 messages
            raw = await ws.recv()
            print(raw)
            print("---")


asyncio.run(main())
```

Lance-le :

```bash
python binance_raw.py
```

Observe le format brut JSON. C'est ce que Binance envoie réellement.

---

## Étape 3 — Identifier les champs

Voici un exemple de payload Binance :

```json
{
  "e": "trade",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "t": 12345,
  "p": "68432.12000000",
  "q": "0.00100000",
  "T": 1672515782136,
  "m": true,
  "M": true
}
```

Correspondance :

| Champ | Signification       |
|-------|---------------------|
| e     | type d'événement    |
| E     | timestamp événement (ms Unix) |
| s     | symbole             |
| t     | trade_id            |
| p     | price               |
| q     | quantity            |
| T     | timestamp du trade (ms Unix)  |
| m     | is_buyer_maker      |

---

## Étape 4 — Parser et afficher proprement

Crée un fichier `binance_parsed.py` :

```python
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
import websockets


BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"


def ms_to_utc(ms: int) -> datetime:
    """Convertit un timestamp Binance (millisecondes Unix) en datetime UTC aware."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def parse_trade(raw: dict) -> dict:
    """
    Mappe le payload brut Binance vers un format propre.
    Note : price et quantity restent en Decimal, jamais en float.
    """
    return {
        "event_time":     ms_to_utc(raw["E"]),
        "symbol":         raw["s"],
        "trade_id":       raw["t"],
        "price":          Decimal(raw["p"]),
        "quantity":       Decimal(raw["q"]),
        "trade_time":     ms_to_utc(raw["T"]),
        "is_buyer_maker": raw["m"],
    }


async def main():
    async with websockets.connect(BINANCE_WS_URL) as ws:
        print("Connecté. En attente de trades...\n")

        async for raw_msg in ws:
            data = json.loads(raw_msg)

            # Ignorer les messages qui ne sont pas des trades
            if data.get("e") != "trade":
                continue

            trade = parse_trade(data)

            print(
                f"[{trade['event_time'].strftime('%H:%M:%S')}] "
                f"{trade['symbol']} | "
                f"prix: {trade['price']:.2f} | "
                f"quantité: {trade['quantity']} | "
                f"maker: {trade['is_buyer_maker']}"
            )


asyncio.run(main())
```

Lance-le :

```bash
python binance_parsed.py
```

Tu dois voir défiler les vrais trades BTCUSDT en temps réel.
Appuie sur Ctrl+C pour arrêter.

---

## Étape 5 — Tester la reconnexion

Coupe ta connexion réseau (mode avion) puis rétablis-la.
Que se passe-t-il ? Le script plante ? Avec quelle erreur ?

C'est normal. En production, il faut gérer cette déconnexion automatiquement.
Tu n'as pas à coder la reconnexion maintenant — juste observer le comportement.

---

## Étape 6 — Compter et mesurer

Modifie `binance_parsed.py` pour afficher toutes les 10 trades :
- le nombre total de trades reçus
- le prix moyen des 10 derniers trades

C'est un exercice libre. Pas de solution imposée.

---

## Questions à te poser avant de regarder la correction

1. Pourquoi convertit-on `price` en `Decimal` et pas en `float` ?
2. Pourquoi les timestamps Binance sont en millisecondes et non en secondes ?
3. Que se passe-t-il si le réseau coupe ? Comment le gérer en production ?
4. Quelle est la différence entre `event_time` (champ `E`) et `trade_time` (champ `T`) ?
   Les deux sont-ils toujours identiques ?
5. Pourquoi filtrer sur `data.get("e") != "trade"` ?
   Quels autres types de messages peut envoyer Binance ?

Note tes réponses. Elles seront comparées dans `corrections/03-binance-ws.md`.
