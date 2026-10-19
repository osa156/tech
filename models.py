"""
SQLAlchemy models for Pacific Crest Estates.

Tables:
- ContactMessage     : general "book a viewing" contact-form submissions
- PropertyEnquiry    : per-property enquiries from the listing modal
- NewsletterSubscriber : newsletter signups in the footer
- PayPalOrder        : simulated PayPal orders (create -> capture lifecycle)
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(120))
    budget = db.Column(db.String(60))
    interest = db.Column(db.String(200))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "budget": self.budget,
            "interest": self.interest,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PropertyEnquiry(db.Model):
    __tablename__ = "property_enquiries"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, nullable=False, index=True)
    property_title = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "property_title": self.property_title,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PayPalOrder(db.Model):
    """Simulated PayPal order. Mirrors the real PayPal Orders v2 lifecycle."""

    __tablename__ = "paypal_orders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    transaction_id = db.Column(db.String(64), unique=True, index=True)
    status = db.Column(db.String(20), default="CREATED", nullable=False)  # CREATED -> COMPLETED / FAILED
    property_id = db.Column(db.Integer)
    property_title = db.Column(db.String(200))
    amount_usd = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    payer_email = db.Column(db.String(120))
    payer_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)
    captured_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "transaction_id": self.transaction_id,
            "status": self.status,
            "property_id": self.property_id,
            "property_title": self.property_title,
            "amount_usd": round(self.amount_usd, 2),
            "currency": self.currency,
            "payer_email": self.payer_email,
            "payer_name": self.payer_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
        }
