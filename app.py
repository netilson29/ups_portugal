from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from functools import wraps
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'troca_esta_chave_para_producao'  # ⚠️ Troca depois por uma chave segura

# -----------------------
# Helpers
# -----------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

def carregar_dados():
    with open("dados.json", "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open("dados.json", "w") as f:
        json.dump(dados, f, indent=4)

# -----------------------
# Rotas públicas
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/rastreio", methods=["POST"])
def rastreio():
    codigo = (request.form.get("codigo") or "").strip().lower()
    dados_json = carregar_dados()
    order = None
    for o in dados_json["orders"]:
        if o["tracking_code"].lower() == codigo or o["client"].lower() == codigo:
            order = o
            break
    if not order:
        flash("Encomenda não encontrada.", "warning")
        return redirect(url_for("home"))

    dados = {
        "cliente": order["client"],
        "codigo": order["tracking_code"],
        "status": order["status"],
        "origem": order["origin"],
        "destino": order["destination"],
        "peso": order["weight"],
        "taxa": order["taxa"],
        "destinatario": order["destinatario"],
        "despachante": order["despachante"],
        "morada": order["morada"],
        "data": order["created_at"],
        "historico": order["history"],
        "lat": order["lat"],
        "lng": order["lng"]
    }
    return render_template("rastreio.html", dados=dados)

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contacto")
def contacto():
    return render_template("contacto.html")

# ✅ Rota de monitoramento para Uptime Robot
@app.route("/health")
def health():
    return "UP", 200

# -----------------------
# Admin
# -----------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", erro="Usuário ou senha inválidos!")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    dados_json = carregar_dados()
    orders = dados_json["orders"]
    return render_template("admin_dashboard.html", orders=orders)

@app.route("/admin/add_order", methods=["POST"])
@admin_required
def add_order():
    dados_json = carregar_dados()
    new_order = {
        "tracking_code": request.form.get("tracking_code"),
        "client": request.form.get("client"),
        "status": request.form.get("status"),
        "origin": request.form.get("origin"),
        "destination": request.form.get("destination"),
        "weight": request.form.get("weight"),
        "taxa": request.form.get("taxa"),
        "destinatario": request.form.get("destinatario"),
        "despachante": request.form.get("despachante"),
        "morada": request.form.get("morada"),
        "created_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        "history": request.form.get("history").splitlines(),
        "lat": float(request.form.get("lat") or 0),
        "lng": float(request.form.get("lng") or 0)
    }
    dados_json["orders"].append(new_order)
    salvar_dados(dados_json)
    flash("Encomenda adicionada com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_order/<string:codigo>")
@admin_required
def delete_order(codigo):
    dados_json = carregar_dados()
    dados_json["orders"] = [o for o in dados_json["orders"] if o["tracking_code"] != codigo]
    salvar_dados(dados_json)
    flash("Encomenda removida.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logout realizado.", "info")
    return redirect(url_for("home"))

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
