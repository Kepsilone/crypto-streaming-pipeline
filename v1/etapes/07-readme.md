# Étape 7 — README final

**Objectif :** rendre le projet présentable sur GitHub.

**Branche :** `feature/readme`

**Durée estimée :** 45 minutes

**Prérequis :** étapes 1 à 6 terminées, captures Grafana disponibles

---

## Contenu obligatoire du README

### 1. Titre et description

```markdown
# Pipeline Streaming Temps Réel — BTCUSDT

Pipeline data engineering événementiel : ingestion WebSocket, transport Kafka,
stockage TimescaleDB, API FastAPI et dashboard Grafana.

Architecture applicable au monitoring industriel, logs machines et flux IoT.
La source de données est le flux public Binance — aucun trading, aucune clé API privée.
```

### 2. Schéma d'architecture

Inclure le schéma ASCII du CLAUDE.md ou une image générée.

### 3. Stack technique

Tableau avec les technologies et leur rôle.

### 4. Lancement rapide

```bash
git clone https://github.com/Kepsilone/pipeline-streaming-crypto
cd pipeline-streaming-crypto
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
pip install -r requirements.txt
python scripts/producer.py &
python scripts/consumer.py
```

### 5. Captures Grafana

Insérer au moins deux captures :
- graphe du prix en temps réel
- graphe du volume par minute

### 6. Structure du repo

Arbre simplifié des dossiers avec une ligne d'explication pour chaque dossier clé.

### 7. Prochaines étapes (V2)

Une section courte sur ce qui est prévu :
- Architecture hexagonale complète
- Tests unitaires et d'intégration
- Multi-symboles
- Prometheus + métriques

---

## Critère de validation

- Le README s'affiche bien sur GitHub (tester avec un aperçu Markdown)
- Les captures sont présentes et visibles
- Les instructions de lancement fonctionnent sur une machine fraîche

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/readme

# ... tu rédiges README.md ...

git add README.md docs/captures/
git commit -m "docs: add project readme with architecture and grafana screenshots"
git checkout develop
git merge feature/readme

# Merger develop dans main quand tout est propre
git checkout main
git merge develop
git tag v1.0.0
git push origin main --tags
```

---

## Statut

- [ ] Terminé
