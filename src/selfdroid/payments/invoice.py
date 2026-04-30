"""
Invoice model for storing payment requests.

Reuses the existing SQLite database via Flask-SQLAlchemy.
"""

from selfdroid import db
from datetime import datetime


class PaymentInvoice(db.Model):
    __tablename__ = "payment_invoice"

    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    order_id = db.Column(db.String(64), unique=True, nullable=False)
    subaddress = db.Column(db.String(95), unique=True, nullable=False)
    subaddress_index = db.Column(db.Integer(), nullable=False)
    amount_xmr = db.Column(db.String(32), nullable=False)
    amount_fiat = db.Column(db.String(32), nullable=False)
    fiat_currency = db.Column(db.String(3), default="usd")
    exchange_rate_at_creation = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), default="pending")
    confirmations = db.Column(db.Integer(), default=0)
    required_confirmations = db.Column(db.Integer(), default=2)
    payment_tx_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(), nullable=False)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "subaddress": self.subaddress,
            "amount_xmr": self.amount_xmr,
            "amount_fiat": self.amount_fiat,
            "fiat_currency": self.fiat_currency,
            "status": self.status,
            "confirmations": self.confirmations,
            "required_confirmations": self.required_confirmations,
            "payment_tx_hash": self.payment_tx_hash,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": self.expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_expired": self.is_expired(),
        }
