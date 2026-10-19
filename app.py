"""
Pacific Crest Estates — Flask API backend (Render.com compatible, pure Python).

Endpoints
---------
GET  /                          -> API info
GET  /api/health                -> health check
GET  /api/properties            -> the 12 featured California listings (JSON)
POST /api/contact               -> save a "book a viewing" contact form
POST /api/enquiry               -> save a per-property enquiry
POST /api/newsletter            -> save a newsletter signup
POST /api/paypal/create-order   -> MOCK PayPal: create an order (holding deposit)
POST /api/paypal/capture-order  -> MOCK PayPal: capture payment for an order
GET  /api/admin/submissions     -> admin dump (requires ?secret=ADMIN_SECRET)

Run locally:
    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:5000

Deploy on Render.com (no Docker):
    Language      : Python 3
    Build Command : pip install -r requirements.txt
    Start Command : gunicorn app:app
    Env Vars      : PYTHON_VERSION=3.11.9  (recommended)
                    SECRET_KEY=<random>
                    ADMIN_SECRET=<random>
                    CORS_ORIGINS=https://your-frontend.com
    (Optional)    : create a Render Postgres instance and link it -> DATABASE_URL
                    is set automatically. Otherwise SQLite is used.
"""
import os
import re
import secrets
import string
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config
from models import (
    ContactMessage,
    NewsletterSubscriber,
    PayPalOrder,
    PropertyEnquiry,
    db,
)

app = Flask(__name__)
app.config.from_object(Config)

# CORS: allow the frontend to call the API from a different origin.
# FRONTEND_URL (set in config / env) is always added to the allowed origins.
_cors_origins = app.config["CORS_ORIGINS"]
_frontend_url = (app.config.get("FRONTEND_URL") or "").rstrip("/")
_placeholder = "https://your-frontend-domain.com"
if _cors_origins == "*":
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    origins = [o.strip().rstrip("/") for o in _cors_origins.split(",") if o.strip()]
    if _frontend_url and _frontend_url != _placeholder and _frontend_url not in origins:
        origins.append(_frontend_url)
    CORS(app, resources={r"/api/*": {"origins": origins}})

db.init_app(app)


# ---------------------------------------------------------------------------
# Property catalogue (single source of truth; frontend mirrors this statically)
# ---------------------------------------------------------------------------
PROPERTIES = [
    {
        "id": 1, "title": "The Bel Air Crest Estate", "type": "Mansion",
        "addr": "Bel Air, Los Angeles, CA", "beds": 7, "baths": 9, "sqft": "18,500",
        "price": "$45,000,000", "price_num": 45.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1000&q=80",
        "desc": "A seven-bedroom modern masterpiece on Bel Air Road with infinity pool, city-to-ocean views, home cinema and a 12-car auto gallery.",
    },
    {
        "id": 2, "title": "Malibu Oceanfront Penthouse", "type": "Penthouse",
        "addr": "Malibu Colony, Malibu, CA", "beds": 5, "baths": 6, "sqft": "6,200",
        "price": "$28,000,000", "price_num": 28.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=80",
        "desc": "A sky residence above Malibu Colony with double-volume living, panoramic Pacific views and a private rooftop terrace with spa.",
    },
    {
        "id": 3, "title": "Beverly Hills Italian Palazzo", "type": "Mansion",
        "addr": "Beverly Park, Beverly Hills, CA", "beds": 8, "baths": 10, "sqft": "21,000",
        "price": "$62,000,000", "price_num": 62.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1000&q=80",
        "desc": "An eight-bedroom Italian-marble palazzo in guard-gated Beverly Park with hand-carved joinery and a grand double staircase.",
    },
    {
        "id": 4, "title": "Carbon Beach Waterfront Villa", "type": "Waterfront Villa",
        "addr": "Carbon Beach, Malibu, CA", "beds": 6, "baths": 7, "sqft": "14,000",
        "price": "$37,000,000", "price_num": 37.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1000&q=80",
        "desc": "A six-bedroom villa on Billionaire's Beach with direct sand frontage, infinity edge pool and disappearing glass walls.",
    },
    {
        "id": 5, "title": "Pacific Heights Sky Residence", "type": "Penthouse",
        "addr": "Pacific Heights, San Francisco, CA", "beds": 4, "baths": 5, "sqft": "4,800",
        "price": "$19,000,000", "price_num": 19.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1000&q=80",
        "desc": "A four-bedroom full-floor penthouse with 270-degree Golden Gate and Bay views, private elevator lobby and terrace.",
    },
    {
        "id": 6, "title": "Atherton Tech Estate", "type": "Mansion",
        "addr": "Atherton, Silicon Valley, CA", "beds": 9, "baths": 12, "sqft": "26,000",
        "price": "$85,000,000", "price_num": 85.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=1000&q=80",
        "desc": "A nine-acre estate in America's most expensive zip code — full smart-home automation, guest house and tennis court.",
    },
    {
        "id": 7, "title": "Laguna Beach Cliffside Manor", "type": "Waterfront Villa",
        "addr": "Laguna Beach, Orange County, CA", "beds": 6, "baths": 8, "sqft": "16,500",
        "price": "$51,000,000", "price_num": 51.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1000&q=80",
        "desc": "A six-bedroom cliffside manor above the Pacific with glass-railed terraces, private beach access and sunset views.",
    },
    {
        "id": 8, "title": "Holmby Hills Grand Estate", "type": "Mansion",
        "addr": "Holmby Hills, Los Angeles, CA", "beds": 10, "baths": 14, "sqft": "32,000",
        "price": "$120,000,000", "price_num": 120.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1000&q=80",
        "desc": "A ten-bedroom trophy estate on one of the largest plots in Holmby Hills — indoor pool, spa, private cinema and guest wing.",
    },
    {
        "id": 9, "title": "Montecito Wine Country Villa", "type": "Mansion",
        "addr": "Montecito, Santa Barbara, CA", "beds": 7, "baths": 9, "sqft": "19,500",
        "price": "$78,000,000", "price_num": 78.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1000&q=80",
        "desc": "A seven-bedroom Mediterranean villa on 5 ocean-view acres with olive grove, pool pavilion and guest casita.",
    },
    {
        "id": 10, "title": "Newport Coast Modern Duplex", "type": "Duplex",
        "addr": "Newport Coast, Orange County, CA", "beds": 5, "baths": 6, "sqft": "5,400",
        "price": "$22,000,000", "price_num": 22.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=1000&q=80",
        "desc": "An elegant five-bedroom ocean-view residence offering the most accessible entry to Newport Coast living.",
    },
    {
        "id": 11, "title": "La Jolla Ridge Signature Estate", "type": "Mansion",
        "addr": "La Jolla, San Diego, CA", "beds": 12, "baths": 16, "sqft": "40,000",
        "price": "$150,000,000", "price_num": 150.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=80",
        "desc": "The signature estate of the collection — twelve bedrooms, 40,000 sq ft, two pools, private tennis court and helipad-ready terrace.",
    },
    {
        "id": 12, "title": "Napa Valley Vineyard Penthouse", "type": "Penthouse",
        "addr": "St. Helena, Napa Valley, CA", "beds": 4, "baths": 5, "sqft": "4,100",
        "price": "$15,000,000", "price_num": 15.0, "unit": "M",
        "img": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1000&q=80",
        "desc": "A refined four-bedroom penthouse loft above a working estate vineyard with wrap-around terrace and wine cellar.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _bad_request(msg):
    return jsonify({"ok": False, "error": msg}), 400


def _gen_id(prefix, length=12):
    alphabet = string.ascii_uppercase + string.digits
    return prefix + "-" + "".join(secrets.choice(alphabet) for _ in range(length))


def _property_by_id(pid):
    for p in PROPERTIES:
        if p["id"] == pid:
            return p
    return None


# ---------------------------------------------------------------------------
# Basic / health / properties
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return jsonify({
        "name": "Pacific Crest Estates API",
        "description": "Luxury California real estate backend (contact, enquiries, newsletter, PayPal-mock deposits).",
        "version": "1.0.0",
        "frontend_url": app.config.get("FRONTEND_URL"),
        "endpoints": [
            "GET  /api/health",
            "GET  /api/properties",
            "POST /api/contact",
            "POST /api/enquiry",
            "POST /api/newsletter",
            "POST /api/paypal/create-order",
            "POST /api/paypal/capture-order",
        ],
    })


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "status": "up", "time": datetime.now(timezone.utc).isoformat()})


@app.route("/api/properties")
def list_properties():
    return jsonify({"ok": True, "count": len(PROPERTIES), "properties": PROPERTIES})


# ---------------------------------------------------------------------------
# Contact form (book a viewing)
# ---------------------------------------------------------------------------
@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    budget = (data.get("budget") or "").strip()
    interest = (data.get("interest") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not phone:
        return _bad_request("name and phone are required")
    if email and not EMAIL_RE.match(email):
        return _bad_request("invalid email format")

    msg = ContactMessage(
        name=name, phone=phone, email=email or None,
        budget=budget or None, interest=interest or None, message=message or None,
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({"ok": True, "id": msg.id, "message": "Thank you — a consultant will contact you within one business hour."}), 201


# ---------------------------------------------------------------------------
# Per-property enquiry
# ---------------------------------------------------------------------------
@app.route("/api/enquiry", methods=["POST"])
def enquiry():
    data = request.get_json(silent=True) or {}
    try:
        property_id = int(data.get("property_id"))
    except (TypeError, ValueError):
        return _bad_request("property_id is required and must be a number")

    prop = _property_by_id(property_id)
    if not prop:
        return _bad_request("unknown property_id")

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not email:
        return _bad_request("name and email are required")
    if not EMAIL_RE.match(email):
        return _bad_request("invalid email format")

    enq = PropertyEnquiry(
        property_id=property_id, property_title=prop["title"],
        name=name, email=email, phone=phone or None, message=message or None,
    )
    db.session.add(enq)
    db.session.commit()
    return jsonify({"ok": True, "id": enq.id, "property": prop["title"],
                    "message": "Enquiry received — we will reply to %s shortly." % email}), 201


# ---------------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------------
@app.route("/api/newsletter", methods=["POST"])
def newsletter():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    if not email or not EMAIL_RE.match(email):
        return _bad_request("a valid email is required")

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if not existing.active:
            existing.active = True
            db.session.commit()
        return jsonify({"ok": True, "message": "You are already subscribed — welcome back."})

    sub = NewsletterSubscriber(email=email)
    db.session.add(sub)
    db.session.commit()
    return jsonify({"ok": True, "id": sub.id, "message": "Subscribed — new listings will arrive in your inbox."}), 201


# ---------------------------------------------------------------------------
# PayPal MOCK — create order
# Mirrors POST https://api-m.sandbox.paypal.com/v2/checkout/orders
# ---------------------------------------------------------------------------
@app.route("/api/paypal/create-order", methods=["POST"])
def paypal_create_order():
    data = request.get_json(silent=True) or {}
    try:
        property_id = int(data.get("property_id"))
    except (TypeError, ValueError):
        return _bad_request("property_id is required")

    prop = _property_by_id(property_id)
    if not prop:
        return _bad_request("unknown property_id")

    payer_email = (data.get("payer_email") or "").strip()
    payer_name = (data.get("payer_name") or "").strip()
    amount = float(data.get("amount") or app.config["HOLDING_DEPOSIT_USD"])
    if amount <= 0:
        return _bad_request("amount must be positive")

    order = PayPalOrder(
        order_id=_gen_id("PAYPAL-MOCK"),
        status="CREATED",
        property_id=property_id,
        property_title=prop["title"],
        amount_usd=amount,
        currency="USD",
        payer_email=payer_email or None,
        payer_name=payer_name or None,
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({
        "ok": True,
        "mode": "MOCK_SIMULATION",
        "order_id": order.order_id,
        "status": order.status,
        "amount": {"value": "%.2f" % amount, "currency_code": "USD"},
        "property": {"id": prop["id"], "title": prop["title"]},
        # In real PayPal you would redirect the buyer to approve_url (a paypal.com link).
        # Here the frontend simulates the PayPal approval screen in a modal.
        "approve_url": "#paypal-mock-approval",
        "expires_in_seconds": 1800,
    }), 201


# ---------------------------------------------------------------------------
# PayPal MOCK — capture order
# Mirrors POST https://api-m.sandbox.paypal.com/v2/checkout/orders/{id}/capture
# ---------------------------------------------------------------------------
@app.route("/api/paypal/capture-order", methods=["POST"])
def paypal_capture_order():
    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or "").strip()
    if not order_id:
        return _bad_request("order_id is required")

    order = PayPalOrder.query.filter_by(order_id=order_id).first()
    if not order:
        return _bad_request("order not found")
    if order.status == "COMPLETED":
        return jsonify({"ok": True, "mode": "MOCK_SIMULATION", "status": "COMPLETED",
                        "transaction_id": order.transaction_id,
                        "amount": {"value": "%.2f" % order.amount_usd, "currency_code": order.currency},
                        "message": "Payment already captured."})

    # Simulate PayPal capture success (integration point: replace with real
    # paypalrestsdk / Orders v2 capture call when going live).
    order.status = "COMPLETED"
    order.transaction_id = _gen_id("TXN-MOCK")
    order.captured_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "ok": True,
        "mode": "MOCK_SIMULATION",
        "status": "COMPLETED",
        "order_id": order.order_id,
        "transaction_id": order.transaction_id,
        "amount": {"value": "%.2f" % order.amount_usd, "currency_code": order.currency},
        "property": {"id": order.property_id, "title": order.property_title},
        "payer_email": order.payer_email,
        "captured_at": order.captured_at.isoformat(),
        "message": "Mock payment captured successfully. No real money was moved.",
    }), 201


# ---------------------------------------------------------------------------
# Admin: dump all submissions (protected by a shared secret query param)
# ---------------------------------------------------------------------------
@app.route("/api/admin/submissions")
def admin_submissions():
    secret = request.args.get("secret", "")
    if secret != app.config["ADMIN_SECRET"]:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    return jsonify({
        "ok": True,
        "contact_messages": [m.to_dict() for m in ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()],
        "property_enquiries": [e.to_dict() for e in PropertyEnquiry.query.order_by(PropertyEnquiry.created_at.desc()).all()],
        "newsletter_subscribers": [s.to_dict() for s in NewsletterSubscriber.query.order_by(NewsletterSubscriber.created_at.desc()).all()],
        "paypal_orders": [o.to_dict() for o in PayPalOrder.query.order_by(PayPalOrder.created_at.desc()).all()],
    })


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    return jsonify({"ok": False, "error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"ok": False, "error": "method not allowed"}), 405


@app.errorhandler(500)
def server_error(_e):
    db.session.rollback()
    return jsonify({"ok": False, "error": "internal server error"}), 500


# Create tables on first run (works for SQLite and Postgres).
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
