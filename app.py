from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'troca_esta_chave_para_producao'  # ⚠️ Troca depois por uma chave segura

# -----------------------
# Configuração do Banco de Dados (Supabase via variável de ambiente)
# -----------------------
db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise RuntimeError("❌ DATABASE_URL não está definida no ambiente!")

# Corrige URL se vier com "postgres://"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------
# Models
# -----------------------
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(250))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    orders = db.relationship('Order', backref='client', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_code = db.Column(db.String(80), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    status = db.Column(db.String(80), default='Em trânsito')
    origin = db.Column(db.String(120))
    destination = db.Column(db.String(120))
    weight = db.Column(db.String(50))
    taxa = db.Column(db.String(50))         # 💰 Taxa
    destinatario = db.Column(db.String(120)) # 📦 Destinatário
    despachante = db.Column(db.String(120)) # 📋 Despachante
    morada = db.Column(db.String(250))      # 🏠 Morada
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    history = db.Column(db.Text)            # Histórico separado por linhas
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

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

# -----------------------
# Rotas públicas
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/rastreio", methods=["POST"])
def rastreio():
    codigo = (request.form.get("codigo") or "").strip()
    order = None
    if codigo:
        order = Order.query.filter_by(tracking_code=codigo).first()
    if not order and codigo:
        order = Order.query.join(Client).filter(Client.name.ilike(f"%{codigo}%")).first()
    if not order:
        flash("Encomenda não encontrada.", "warning")
        return redirect(url_for("home"))

    dados = {
        "cliente": order.client.name,
        "codigo": order.tracking_code,
        "status": order.status,
        "origem": order.origin,
        "destino": order.destination,
        "peso": order.weight,
        "taxa": order.taxa,
        "destinatario": order.destinatario,
        "despachante": order.despachante,
        "morada": order.morada,
        "data": order.created_at.strftime("%d/%m/%Y %H:%M"),
        "historico": order.history.splitlines() if order.history else [],
        "lat": order.lat,
        "lng": order.lng
    }
    return render_template("rastreio.html", dados=dados)

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contacto")
def contacto():
    return render_template("contacto.html")

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
    clients = Client.query.order_by(Client.name).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_dashboard.html", clients=clients, orders=orders)

@app.route("/admin/add_client", methods=["POST"])
@admin_required
def add_client():
    name = request.form.get("name")
    address = request.form.get("address")
    phone = request.form.get("phone")
    email = request.form.get("email")
    if not name:
        flash("O nome do cliente é obrigatório.", "danger")
        return redirect(url_for("admin_dashboard"))
    client = Client(name=name, address=address, phone=phone, email=email)
    db.session.add(client)
    db.session.commit()
    flash("Cliente adicionado com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/add_order", methods=["POST"])
@admin_required
def add_order():
    tracking_code = request.form.get("tracking_code")
    client_id = request.form.get("client_id")
    status = request.form.get("status")
    origin = request.form.get("origin")
    destination = request.form.get("destination")
    weight = request.form.get("weight")
    taxa = request.form.get("taxa")
    destinatario = request.form.get("destinatario")
    despachante = request.form.get("despachante")
    morada = request.form.get("morada")
    history = request.form.get("history")
    lat = request.form.get("lat")
    lng = request.form.get("lng")

    if not tracking_code or not client_id:
        flash("Código de rastreio e cliente são obrigatórios.", "danger")
        return redirect(url_for("admin_dashboard"))

    if Order.query.filter_by(tracking_code=tracking_code).first():
        flash("Já existe uma encomenda com esse código.", "danger")
        return redirect(url_for("admin_dashboard"))

    order = Order(
        tracking_code=tracking_code,
        client_id=int(client_id),
        status=status or "Em trânsito",
        origin=origin,
        destination=destination,
        weight=weight,
        taxa=taxa,
        destinatario=destinatario,
        despachante=despachante,
        morada=morada,
        history=history,
        lat=float(lat) if lat else None,
        lng=float(lng) if lng else None
    )
    db.session.add(order)
    db.session.commit()
    flash("Encomenda adicionada com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_order/<int:id>")
@admin_required
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
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
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
