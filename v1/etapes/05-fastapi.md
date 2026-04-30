# Étape 5 — FastAPI

**Objectif :** exposer les données via une API HTTP minimale.

**Branche :** `feature/fastapi`

**Durée estimée :** 45 minutes

**Prérequis :** étape 4 terminée

---

## Fichier à créer

```
src/api/app.py
```

---

## Endpoints à implémenter

Trois routes uniquement :

| Endpoint             | Réponse attendue                              |
|----------------------|-----------------------------------------------|
| GET /health          | `{"status": "ok", "db": "connected"}`         |
| GET /trades/latest   | liste des 50 derniers trades                  |
| GET /trades/count    | `{"count": 12345}`                            |

---

## Lancement

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

---

## Critère de validation

```bash
curl http://localhost:8000/health
# → {"status": "ok", "db": "connected"}

curl http://localhost:8000/trades/count
# → {"count": 12345}

curl http://localhost:8000/trades/latest
# → [{...}, {...}, ...]
```

La documentation auto-générée doit être accessible sur `http://localhost:8000/docs`.

---

## Commandes Git

```bash
git checkout develop
git checkout -b feature/fastapi

# ... tu codes src/api/app.py ...

git add src/api/app.py
git commit -m "feat: add fastapi with health, trades/latest and trades/count"
git checkout develop
git merge feature/fastapi
```

---

## Statut

- [ ] Terminé
