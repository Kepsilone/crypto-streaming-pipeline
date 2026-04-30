# Étape 6 — Grafana

**Objectif :** créer un dashboard qui affiche les trades en temps réel.

**Branche :** `feature/grafana`

**Durée estimée :** 60 minutes

**Prérequis :** étape 5 terminée, données en base

---

## Connexion à TimescaleDB depuis Grafana

1. Ouvrir `http://localhost:3000` (admin / admin)
2. Aller dans **Connections → Data sources → Add data source**
3. Choisir **PostgreSQL**
4. Remplir :
   - Host : `timescaledb:5432`
   - Database : `crypto`
   - User : `user`
   - Password : `password`
   - SSL Mode : `disable`
5. Cliquer **Save & test** → doit afficher "Database Connection OK"

---

## Panels à créer

### Panel 1 — Prix en temps réel (Time series)

```sql
SELECT
  event_time AS time,
  price::float AS prix
FROM trades
WHERE $__timeFilter(event_time)
  AND symbol = 'BTCUSDT'
ORDER BY event_time ASC
```

### Panel 2 — Volume par minute (Bar chart)

```sql
SELECT
  time_bucket('1 minute', event_time) AS time,
  SUM(quantity)::float AS volume
FROM trades
WHERE $__timeFilter(event_time)
  AND symbol = 'BTCUSDT'
GROUP BY 1
ORDER BY 1 ASC
```

### Panel 3 — Nombre total de trades (Stat)

```sql
SELECT COUNT(*) AS total FROM trades
```

### Panel 4 — Dernier prix (Stat)

```sql
SELECT price::float AS "dernier prix"
FROM trades
ORDER BY event_time DESC
LIMIT 1
```

---

## Exporter le dashboard

Une fois satisfait du dashboard :
1. Cliquer sur l'icône de partage (Share) en haut à droite du dashboard
2. Aller dans **Export → Save to file**
3. Copier le fichier JSON dans `grafana/dashboards/crypto.json`

---

## Critère de validation

- Le dashboard affiche des données réelles qui se mettent à jour
- Le fichier `grafana/dashboards/crypto.json` est commité dans le repo
- Une capture d'écran est sauvegardée dans `docs/captures/grafana.png`

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/grafana

# ... tu crées le dashboard et exportes le JSON ...

mkdir -p docs/captures
git add grafana/dashboards/crypto.json docs/captures/
git commit -m "feat: add grafana dashboard with price and volume panels"
git checkout develop
git merge feature/grafana
```

---

## Statut

- [ ] Terminé
