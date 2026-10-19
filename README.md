# Site de sondage participatif

Application web Flask où les visiteurs proposent des sondages, un administrateur les valide, puis chacun peut voter une seule fois.

## Fonctionnalités

- Proposition de sondages par les visiteurs (`/proposer`)
- Modération par un administrateur : valider, refuser, clôturer (`/admin`)
- Vote unique par navigateur, grâce à un cookie anonyme (sans création de compte)
- Historique des sondages clôturés (`/historique`)
- API REST en JSON

## Stack

Python · Flask · JavaScript · HTML / CSS · stockage JSON

## Lancer le projet en local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (sous Linux/macOS : source .venv/bin/activate)
pip install -r requirements.txt

# Variables d'environnement (voir .env.example)
set SECRET_KEY=une-cle-aleatoire
set ADMIN_PASSWORD=votre-mot-de-passe

python app.py
```

L'application est disponible sur http://localhost:5000. Sans `ADMIN_PASSWORD`, la connexion à l'espace d'administration est désactivée.

## Sécurité

- Aucun mot de passe dans le code : identifiants admin et clé de session lus depuis l'environnement
- Routes d'administration de l'API protégées par la session (réponse 401 sinon)
- Les identifiants des votants ne sont jamais renvoyés par l'API publique

## Tests

```bash
pip install pytest
pytest
```

## API

| Méthode | Route | Accès |
|---|---|---|
| GET | `/api/polls` | public |
| GET | `/api/polls/expired` | public |
| POST | `/api/proposer` | public |
| POST | `/api/vote/<sondage>/<option>` | public (une fois par navigateur) |
| GET | `/api/polls/pending` | admin |
| POST | `/api/admin/create` | admin |
| POST | `/api/polls/validate/<index>` | admin |
| POST | `/api/polls/expire/<index>` | admin |
| DELETE | `/api/polls/refuse/<index>` | admin |
