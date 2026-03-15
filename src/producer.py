# 1. Se connecter à Binance WebSocket
# 2. Recevoir les messages JSON
# 3. Afficher prix, quantité, timestamp

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