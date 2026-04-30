# Étape 1 — Binance WebSocket → console

**Objectif :** afficher les trades BTCUSDT en temps réel dans le terminal.

**Branche :** `feature/binance-websocket-console`

**Durée estimée :** 30 minutes

**Prérequis :** étape 0 terminée

---

## Fichier à créer

```
scripts/producer.py
```

Un seul fichier. Pas de classe, pas d'architecture. Script procédural.

---

## Ce que le script doit faire

1. Se connecter au WebSocket Binance (`wss://stream.binance.com:9443/ws/btcusdt@trade`)
2. Recevoir chaque message
3. Vérifier que c'est bien un trade (`"e": "trade"`)
4. Parser les champs utiles (voir mapping dans CLAUDE.md)
5. Afficher une ligne lisible dans le terminal
6. Se reconnecter automatiquement si la connexion est perdue

---

## Ce que le script ne doit PAS faire à cette étape

- Publier dans Kafka
- Insérer en base
- Utiliser des classes ou des ports
- Gérer la config via pydantic-settings

---

## Critère de validation

Quand tu lances `python scripts/producer.py`, tu vois défiler des lignes comme :

```
[14:23:01] BTCUSDT | prix: 68432.12 | quantité: 0.00100 | maker: True
[14:23:01] BTCUSDT | prix: 68431.50 | quantité: 0.00250 | maker: False
[14:23:02] BTCUSDT | prix: 68433.00 | quantité: 0.00050 | maker: True
```

---

## Rappel — mapping Binance

| Champ JSON | Variable Python | Conversion                              |
|------------|-----------------|------------------------------------------|
| E          | event_time      | `datetime.fromtimestamp(E/1000, tz=UTC)` |
| s          | symbol          | tel quel                                 |
| t          | trade_id        | `int`                                    |
| p          | price           | `Decimal`                                |
| q          | quantity        | `Decimal`                                |
| T          | trade_time      | `datetime.fromtimestamp(T/1000, tz=UTC)` |
| m          | is_buyer_maker  | `bool`                                   |

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/binance-websocket-console

# ... tu codes scripts/producer.py ...

git add scripts/producer.py
git commit -m "feat: read btcusdt trades from binance websocket"
git checkout develop
git merge feature/binance-websocket-console
```

---

## Statut

- [ ] Terminé
