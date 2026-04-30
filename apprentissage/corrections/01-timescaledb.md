# Correction 01 — TimescaleDB

**À lire après avoir fait l'exercice.**

---

## Réponses aux questions

**1. Qu'est-ce qu'une hypertable par rapport à une table normale ?**

Une table PostgreSQL classique stocke toutes les données dans un seul bloc.
Une hypertable TimescaleDB partitionne automatiquement les données par intervalles
de temps (chunks). Par exemple : un chunk par semaine. Cela permet des requêtes
beaucoup plus rapides sur des plages temporelles ("les trades de la semaine dernière")
car TimescaleDB ne lit que les chunks concernés, pas toute la table.

Pour toi dans le projet : quand tu requêtes les dernières 5 minutes de trades,
TimescaleDB ne lit qu'un seul chunk au lieu de scanner toute la table.

**2. Pourquoi TIMESTAMPTZ plutôt que TIMESTAMP ?**

`TIMESTAMP` stocke une date et une heure sans information de fuseau horaire.
`TIMESTAMPTZ` (timestamp with time zone) stocke la date en UTC et convertit
automatiquement à l'affichage selon le fuseau de la session.

Dans un pipeline distribué (Binance au Japon, Kafka en Europe, TimescaleDB en local,
Grafana ailleurs), tout le monde parle UTC. Sans `TIMESTAMPTZ`, tu peux avoir des
décalages silencieux difficiles à déboguer.

**3. Que fait ON CONFLICT DO NOTHING exactement ?**

Si tu essaies d'insérer un enregistrement dont la clé primaire existe déjà,
au lieu de lever une erreur `duplicate key`, PostgreSQL ignore silencieusement
l'insertion et continue.

C'est ce qu'on appelle l'idempotence : tu peux rejouer la même insertion
100 fois, le résultat est identique. Crucial quand Kafka rejoue des messages
après un redémarrage du consumer.

**4. Pourquoi NUMERIC et pas FLOAT ?**

`FLOAT` est un nombre à virgule flottante binaire. Il introduit des erreurs
d'arrondi imperceptibles mais réelles :

```python
>>> 68432.12 * 0.001
68.43212000000001   # pas 68.43212
```

Sur des calculs financiers (volume total, prix moyen), ces erreurs s'accumulent.
`NUMERIC` stocke les décimales exactement comme elles sont écrites.
Binance envoie les prix comme des strings (`"68432.12000000"`) précisément
pour éviter ce problème — il faut le respecter en base.

---

## Erreurs fréquentes à cet exercice

**"ERROR: could not open extension control file"**
L'extension TimescaleDB n'est pas disponible. Vérifie que tu utilises bien
l'image `timescale/timescaledb:latest-pg15` et non l'image PostgreSQL officielle.

**"ERROR: relation "trades" already exists"**
Tu as déjà créé la table lors d'un essai précédent. Soit tu la supprimes
(`DROP TABLE trades;`), soit tu utilises `CREATE TABLE IF NOT EXISTS`.

**"could not connect to server"**
Le container n'est pas encore prêt. Attends 5 secondes et réessaie.
