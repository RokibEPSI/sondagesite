from flask import Flask, request, jsonify, render_template, flash, url_for, redirect, session
from flask_cors import CORS
from datetime import timedelta
from functools import wraps
import hmac
import json, os
import secrets
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)

#  Clé secrète lue depuis l'environnement ; sinon clé aléatoire (les sessions ne survivent pas à un redémarrage)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(minutes=30)

CORS(app)

# ----------- CONFIG BASE DE DONNÉES -----------
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Render fournit postgres://, SQLAlchemy veut postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # Local fallback → SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///polls.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------- FICHIER JSON POUR LES SONDAGES -----------
DATA_FILE = "polls.json"

def load_polls():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_polls(polls):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(polls, f, indent=2, ensure_ascii=False)

def public_poll(poll):
    """Retire la liste des votants (identifiants de cookies) avant d'envoyer un sondage au navigateur."""
    return {key: value for key, value in poll.items() if key != "voters"}


def admin_required(view):
    """Réserve une route de l'API à l'administrateur connecté."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return jsonify({"error": "Authentification administrateur requise"}), 401
        return view(*args, **kwargs)
    return wrapper


@app.after_request
def assign_user_cookie(response):
    # Posé après la réponse : la première visite affiche bien la page (avant, elle était vide)
    if not request.cookies.get("user_id"):
        response.set_cookie(
            "user_id", str(uuid.uuid4()), max_age=60*60*24*365, httponly=True, samesite="Lax"
        )  # cookie valable 1 an
    return response
# ----------- ROUTES UTILISATEUR -----------
@app.route("/api/polls", methods=["GET"])
def get_active_polls():
    polls = [public_poll(p) for p in load_polls() if p.get("status") == "active"]
    return jsonify(polls)


@app.route("/api/polls/expired", methods=["GET"])
def get_expired_polls():
    polls = [public_poll(p) for p in load_polls() if p.get("status") == "expired"]
    return jsonify(polls)


@app.route("/api/proposer", methods=["POST"])
def proposer_poll():
    data = request.json
    if not data.get("question") or not data.get("options"):
        return jsonify({"error": "Champs manquants"}), 400

    polls = load_polls()
    polls.append({
        "question": data["question"],
        "options": [{"text": opt, "votes": 0} for opt in data["options"]],
        "status": "pending",
        "voters": []
    })
    save_polls(polls)
    return jsonify({"message": "Votre proposition a été envoyée à l'administrateur"}), 201


@app.route("/api/vote/<int:poll_id>/<int:option_index>", methods=["POST"])
def vote(poll_id, option_index):
    user_id = request.cookies.get("user_id")  # identifiant unique du navigateur
    if not user_id:
        return jsonify({"error": "Utilisateur non identifié"}), 400

    polls = load_polls()
    active_polls = [p for p in polls if p.get("status") == "active"]

    if poll_id >= len(active_polls):
        return jsonify({"error": "Sondage inexistant"}), 404

    poll = active_polls[poll_id]

    if option_index >= len(poll["options"]):
        return jsonify({"error": "Option inexistante"}), 404

    if user_id in poll.get("voters", []):
        return jsonify({"error": "Vous avez déjà voté"}), 403

    poll["options"][option_index]["votes"] += 1
    poll.setdefault("voters", []).append(user_id)

    save_polls(polls)
    return jsonify({"message": "Vote enregistré"}), 200

# ----------- ROUTES ADMIN -----------
@app.route("/api/polls/pending", methods=["GET"])
@admin_required
def get_pending():
    polls = [public_poll(p) for p in load_polls() if p.get("status") == "pending"]
    return jsonify(polls)


@app.route("/api/polls/validate/<int:index>", methods=["POST"])
@admin_required
def validate_poll(index):
    polls = load_polls()
    pending_polls = [p for p in polls if p.get("status") == "pending"]

    if index >= len(pending_polls):
        return jsonify({"error": "Sondage inexistant"}), 404

    poll = pending_polls[index]
    poll["status"] = "active"
    save_polls(polls)
    return jsonify({"message": "Sondage validé"}), 200


@app.route("/api/admin/create", methods=["POST"])
@admin_required
def admin_create_poll():
    data = request.json
    if not data.get("question") or not data.get("options"):
        return jsonify({"error": "Champs manquants"}), 400

    polls = load_polls()
    polls.append({
        "question": data["question"],
        "options": [{"text": opt, "votes": 0} for opt in data["options"]],
        "status": "active",
        "voters": []
    })
    save_polls(polls)
    return jsonify({"message": "Sondage créé et activé"}), 201


@app.route("/api/polls/expire/<int:index>", methods=["POST"])
@admin_required
def expire_poll(index):
    polls = load_polls()
    active_polls = [p for p in polls if p.get("status") == "active"]

    if index >= len(active_polls):
        return jsonify({"error": "Sondage inexistant"}), 404

    poll = active_polls[index]
    poll["status"] = "expired"
    save_polls(polls)
    return jsonify({"message": "Sondage expiré"}), 200


@app.route("/api/polls/refuse/<int:index>", methods=["DELETE"])
@admin_required
def refuse_poll(index):
    polls = load_polls()
    pending_polls = [p for p in polls if p.get("status") == "pending"]

    if index >= len(pending_polls):
        return jsonify({"error": "Sondage inexistant"}), 404

    poll_to_remove = pending_polls[index]
    polls.remove(poll_to_remove)
    save_polls(polls)

    return jsonify({"message": "Sondage supprimé / refusé"}), 200


# ----------- AUTH ADMIN -----------
# Identifiants lus depuis l'environnement (voir .env.example) : plus aucun mot de passe dans le code.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")


def check_admin_credentials(user, pwd):
    if not ADMIN_PASSWORD:
        return False  # connexion admin désactivée tant qu'ADMIN_PASSWORD n'est pas défini
    # compare_digest évite de deviner le mot de passe en mesurant le temps de réponse
    return hmac.compare_digest(user, ADMIN_USERNAME) and hmac.compare_digest(pwd, ADMIN_PASSWORD)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pwd = request.form.get("password", "")

        if check_admin_credentials(user, pwd):
            session.permanent = True
            session["admin"] = True
            flash("Connexion réussie", "success")
            return redirect(url_for("admin_page"))
        else:
            flash("Identifiants invalides", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Déconnecté", "info")
    return redirect(url_for("login"))


@app.route("/admin")
def admin_page():
    if "admin" not in session:
        flash("Veuillez vous connecter pour accéder à l'administration", "warning")
        return redirect(url_for("login"))
    return render_template("admin.html")


# ----------- ROUTES PAGES HTML -----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/proposer")
def proposer_page():
    return render_template("proposer.html")


@app.route("/historique")
def historique_page():
    return render_template("historique.html")


# ----------- MAIN -----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
