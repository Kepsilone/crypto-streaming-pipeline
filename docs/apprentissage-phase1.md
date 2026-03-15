# Apprentissage — Phase 1 : Binance WebSocket

## Ce que j'ai appris

Connecter un script Python à une source de données temps réel via WebSocket,
recevoir des messages JSON et les afficher proprement dans le terminal.

---

## Concepts clés

### WebSocket
Connexion permanente entre ton programme et un serveur.
Contrairement à une requête HTTP classique (tu demandes → tu reçois → terminé),
le WebSocket reste ouvert et le serveur envoie des données en continu.

### JSON
Format de données texte universel. Binance envoie ses messages dans ce format :
```json
{"p": "71690.46", "q": "0.001", "T": 1773553271269}
```
Python ne peut pas lire ce texte directement — `json.loads()` le transforme en dictionnaire.

### Dictionnaire Python
Structure qui stocke des données en paires clé → valeur.
```python
data = {"p": "71690.46", "q": "0.001"}
data["p"]  # → "71690.46"
data["q"]  # → "0.001"
```
On accède à une valeur avec des crochets `[ ]` et la clé entre guillemets.

### async / await
Python exécute normalement une ligne à la fois.
Avec `async`, il peut attendre des données réseau sans bloquer le reste du programme.
- `async def` → fonction qui peut attendre
- `async with` → ouvre une ressource et la ferme automatiquement
- `async for` → boucle qui attend chaque nouvel élément

### f-string
Texte avec variables intégrées.
```python
prix = 71690.46
print(f"Prix : {prix} USDT")  # → Prix : 71690.46 USDT
```
Le `f` devant les guillemets active les accolades `{ }` pour insérer des variables.

---

## Symboles Python — résumé

| Symbole | Rôle | Exemple |
|---------|------|---------|
| `" "` | délimite du texte | `"bonjour"` |
| `( )` | appel de fonction / paramètres | `print("hello")` |
| `[ ]` | accès à un dictionnaire ou liste | `data["p"]` |
| `{ }` | dans un f-string : insère une variable | `f"{prix}"` |
| `:` | début d'un bloc de code | `def connect():` |
| indentation | définit ce qui est dans un bloc | 4 espaces |

---

## Commandes Git apprises

| Commande | Rôle |
|----------|------|
| `git clone <url>` | copie un repo GitHub sur ton PC — première fois uniquement |
| `git add <fichier>` | sélectionne un fichier à sauvegarder |
| `git commit -m "message"` | crée un point de sauvegarde avec un message |
| `git pull --rebase` | récupère les changements de GitHub vers ton PC |
| `git push` | envoie tes changements vers GitHub |

### Flux normal à retenir
```
tu codes → git add → git commit → git pull → git push
```

### Convention de commits
```
feat(producer): connect binance websocket and stream trades
├── feat      = nouvelle fonctionnalité
├── producer  = le composant concerné
└── message   = ce que ça fait, en anglais, court
```

Types : `feat`, `fix`, `docs`, `chore`, `test`, `refactor`

---

## Le code complet expliqué

```python
# Outils pour gérer les tâches qui attendent (connexion réseau)
import asyncio

# Outil pour lire et transformer du JSON en données Python
import json

# Lib pour ouvrir une connexion WebSocket
import websockets

# Outil pour convertir un timestamp en date lisible
from datetime import datetime

# Adresse du flux Binance — trades BTC/USDT en temps réel
URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"

# Fonction principale — async car elle attend des données réseau
async def connect():

    # Ouvre la connexion WebSocket et la ferme automatiquement à la fin
    async with websockets.connect(URL) as ws:
        print("Connecté à Binance")

        # Boucle infinie — attend chaque nouveau message de Binance
        async for message in ws:

            # Transforme le texte JSON brut en dictionnaire Python
            data = json.loads(message)

            # Convertit le timestamp millisecondes en date lisible
            ts = datetime.fromtimestamp(data["T"] / 1000)

            # Extrait le prix et la quantité depuis le dictionnaire
            prix = float(data["p"])
            quantite = float(data["q"])

            # Affiche les données formatées dans le terminal
            print(f"{ts} | prix: {prix} USDT | quantité: {quantite}")

# Point d'entrée — démarre le programme
asyncio.run(connect())
```

### Les champs Binance utilisés

| Champ | Signification | Type reçu | Traitement |
|-------|--------------|-----------|------------|
| `T` | timestamp en millisecondes | entier | `/ 1000` pour convertir en secondes |
| `p` | prix | texte | `float()` pour convertir en nombre |
| `q` | quantité | texte | `float()` pour convertir en nombre |

---

## Ce que je suis capable de refaire

- [ ] Créer un repo GitHub et le cloner localement
- [ ] Installer une lib Python avec `pip`
- [ ] Écrire une fonction `async` qui se connecte à un WebSocket
- [ ] Lire un champ dans un dictionnaire Python
- [ ] Afficher des données formatées avec un f-string
- [ ] Committer et pousser sur GitHub

---

## Phase suivante

**Phase 2** — envoyer ces messages dans Kafka au lieu de les afficher dans le terminal.
