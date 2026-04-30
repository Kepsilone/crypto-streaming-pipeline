# Correction 03 — Binance WebSocket

**À lire après avoir fait l'exercice.**

---

## Réponses aux questions

**1. Pourquoi Decimal et pas float ?**

Binance envoie les prix sous forme de string : `"68432.12000000"`.
Ce n'est pas un hasard — c'est précisément pour éviter les erreurs de virgule flottante.

```python
>>> float("68432.12000000")
68432.12             # Python arrondit silencieusement

>>> from decimal import Decimal
>>> Decimal("68432.12000000")
Decimal('68432.12000000')   # précision exacte conservée
```

Dans un pipeline financier, même une erreur de 0.00000001 sur le prix
se multiplie sur des milliers de trades. `Decimal` garantit la précision exacte.

**2. Pourquoi les timestamps Binance sont en millisecondes ?**

La précision à la seconde ne suffit pas pour des trades financiers.
Plusieurs trades peuvent avoir lieu dans la même seconde. Les millisecondes
permettent de les ordonner correctement et de mesurer des délais d'exécution
inférieurs à une seconde.

Convention : `E = 1672515782136` signifie 1672515782 secondes + 136 millisecondes
depuis le 1er janvier 1970 UTC. D'où la division par 1000 avant `fromtimestamp()`.

**3. Que se passe-t-il si le réseau coupe ?**

Sans gestion d'erreur, `websockets.connect()` lève une exception
`websockets.exceptions.ConnectionClosedError` ou `ConnectionResetError`.
Le script s'arrête.

En production, il faut une boucle de reconnexion avec backoff exponentiel :

```python
import asyncio
import websockets

async def main():
    retry_delay = 1
    while True:
        try:
            async with websockets.connect(BINANCE_WS_URL) as ws:
                retry_delay = 1  # reset si connexion réussie
                async for msg in ws:
                    # traitement...
                    pass
        except (websockets.exceptions.ConnectionClosed, OSError) as e:
            print(f"Déconnecté : {e}. Reconnexion dans {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # max 60 secondes
```

C'est exactement ce que l'adapter `binance/websocket_reader.py` devra faire
dans le projet.

**4. Différence entre event_time (E) et trade_time (T) ?**

- `T` (trade_time) : moment exact où le trade a été exécuté sur le marché Binance.
- `E` (event_time) : moment où Binance a généré et envoyé l'événement WebSocket.

Ils sont souvent identiques ou très proches (quelques millisecondes d'écart).
Mais en cas de charge élevée sur les serveurs Binance, `E` peut être légèrement
postérieur à `T`. Pour mesurer la latence d'ingestion, on compare `event_time`
avec `inserted_at` (horodatage de l'insertion en base).

**5. Pourquoi filtrer sur data.get("e") != "trade" ?**

Binance peut envoyer d'autres types de messages sur la même connexion WebSocket :

- Messages de contrôle de la connexion
- Réponses aux pings (heartbeat)
- Erreurs de stream

Si tu ne filtres pas, tu risques de tenter de parser un message de ping comme
un trade, ce qui lèverait un `KeyError` sur `data["p"]` ou `data["t"]`.

La règle : toujours vérifier le type d'événement avant de parser.

---

## Réponse à l'étape 6 — Compter et mesurer

Exemple d'implémentation :

```python
from collections import deque

prices = deque(maxlen=10)  # garde les 10 derniers prix
count = 0

async for raw_msg in ws:
    data = json.loads(raw_msg)
    if data.get("e") != "trade":
        continue

    trade = parse_trade(data)
    count += 1
    prices.append(trade["price"])

    if count % 10 == 0:
        avg = sum(prices) / len(prices)
        print(f"Total reçus : {count} | Prix moyen (10 derniers) : {avg:.2f}")
```

---

## Erreurs fréquentes à cet exercice

**"ssl.SSLError" ou "certificate verify failed"**
Problème de certificat SSL sur certaines configs Windows.
Solution : `websockets.connect(BINANCE_WS_URL, ssl=True)` ou mettre à jour
les certificats Python avec `pip install certifi`.

**Pas de messages qui arrivent**
Binance n'envoie des trades que quand il y a de l'activité sur la paire.
BTCUSDT est très actif — si tu ne vois rien après 5 secondes, vérifie
l'URL du stream.

**"decimal.InvalidOperation"**
Le champ `p` ou `q` est vide ou mal formé. Ajoute une validation :
```python
if not raw.get("p") or not raw.get("q"):
    raise ValueError("Prix ou quantité manquant")
```
