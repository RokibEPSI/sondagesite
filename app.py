from flask import Flask, request, jsonify, render_template, flash, url_for, redirect, session
from flask_cors import CORS
from datetime import timedelta
import json, os

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# 🔑 Clé secrète sécurisée (prend depuis ENV, sinon fallback)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")
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


# ----------- ROUTES UTILISATEUR -----------
@app.route("/api/polls", methods=["GET"])
def get_active_polls():
    polls = [p for p in load_polls() if p.get("status") == "active"]
    return jsonify(polls)


@app.route("/api/polls/expired", methods=["GET"])
def get_expired_polls():
    polls = [p for p in load_polls() if p.get("status") == "expired"]
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
    user_ip = request.remote_addr
    polls = load_polls()
    active_polls = [p for p in polls if p.get("status") == "active"]

    if poll_id >= len(active_polls):
        return jsonify({"error": "Sondage inexistant"}), 404

    poll = active_polls[poll_id]

    if user_ip in poll.get("voters", []):
        return jsonify({"error": "Vous avez déjà voté"}), 403

    poll["options"][option_index]["votes"] += 1
    poll["voters"].append(user_ip)

    save_polls(polls)
    return jsonify({"message": "Vote enregistré"}), 200


# ----------- ROUTES ADMIN -----------
@app.route("/api/polls/pending", methods=["GET"])
def get_pending():
    polls = [p for p in load_polls() if p.get("status") == "pending"]
    return jsonify(polls)


@app.route("/api/polls/validate/<int:index>", methods=["POST"])
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
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "sondage.25"
}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        if user == ADMIN_CREDENTIALS["username"] and pwd == ADMIN_CREDENTIALS["password"]:
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
