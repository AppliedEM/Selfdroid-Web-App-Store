"""
Flask blueprint for payment-related endpoints.

Routes:
- /web/payment-checkout (GET/POST) - Create payment invoice
- /web/payment-status/<invoice_id> (GET) - Check payment status
- /web/payment-qr/<invoice_id> (GET) - Get QR code data
- /web/payment-webhook (POST) - External webhook receiver (optional)
"""

import logging
import qrcode
import io
import base64
from decimal import Decimal
from flask import (
    Blueprint, request, jsonify, render_template, url_for,
    redirect, send_file
)
from selfdroid.EndpointExecutor import EndpointExecutor
from selfdroid.web.authenticator.WebAuthenticator import WebAuthenticator
from selfdroid.payments.invoice import PaymentInvoice
from selfdroid.payments.gateway import gateway
from selfdroid.payments.exchange import xmr_to_fiat, fiat_to_xmr
from selfdroid import db

logger = logging.getLogger(__name__)

web_payments_blueprint = Blueprint(
    "web_payments_blueprint", __name__, url_prefix="/web"
)


@web_payments_blueprint.route("/payment-checkout", methods=["GET", "POST"])
def fl_web_payment_checkout():
    """
    Create a payment invoice for an order.

    GET: Show payment form (enter order ID, amount, currency)
    POST: Create invoice, show payment details with QR code
    """
    auth = WebAuthenticator()
    if not auth.has_admin_privileges():
        return redirect(url_for("web_blueprint.fl_web_login"))

    if request.method == "GET":
        return render_template(
            "payments/payment_checkout.html",
        )

    order_id = request.form.get("order_id", "")
    amount_fiat = request.form.get("amount_fiat", "0")
    currency = request.form.get("currency", "usd").lower()

    if not order_id or not amount_fiat:
        return render_template(
            "payments/payment_checkout.html",
            error="Order ID and amount are required.",
        )

    try:
        amount_fiat_decimal = Decimal(amount_fiat)
        if amount_fiat_decimal <= 0:
            raise ValueError("Amount must be positive")

        xmr_amount = fiat_to_xmr(amount_fiat_decimal, currency)

        label = f"Selfdroid Order #{order_id}"
        address, sub_index = gateway.create_invoice_address(label)

        rate = gateway.get_xmr_usd_rate() if currency == "usd" else gateway._get_rate(currency)

        from datetime import datetime, timedelta
        invoice = PaymentInvoice(
            order_id=order_id,
            subaddress=address,
            subaddress_index=sub_index,
            amount_xmr=str(xmr_amount),
            amount_fiat=str(amount_fiat_decimal),
            fiat_currency=currency,
            exchange_rate_at_creation=str(rate),
            status="pending",
            required_confirmations=2,
            expires_at=datetime.utcnow() + timedelta(seconds=86400),
        )
        db.session.add(invoice)
        db.session.commit()

        payment_uri = gateway.generate_payment_uri(address, Decimal(xmr_amount), label)

        qr = qrcode.make(payment_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return render_template(
            "payments/payment_invoice.html",
            invoice=invoice,
            payment_uri=payment_uri,
            qr_base64=qr_base64,
            fiat_amount=str(amount_fiat_decimal),
            currency_symbol={"usd": "$", "eur": "EUR", "gbp": "GBP"}.get(currency, currency.upper()),
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating payment invoice: {e}")
        return render_template(
            "payments/payment_checkout.html",
            error=str(e),
        )


@web_payments_blueprint.route("/payment-status/<int:invoice_id>", methods=["GET"])
def fl_web_payment_status(invoice_id):
    """Check the status of a payment invoice."""
    invoice = PaymentInvoice.query.get_or_404(invoice_id)
    result = gateway.check_payment(
        invoice.subaddress,
        Decimal(invoice.amount_xmr),
        invoice.required_confirmations,
    )
    return jsonify({
        **invoice.to_dict(),
        "payment_check": result,
    })


@web_payments_blueprint.route("/payment-qr/<int:invoice_id>", methods=["GET"])
def fl_web_payment_qr(invoice_id):
    """Return a QR code image for a payment invoice."""
    invoice = PaymentInvoice.query.get_or_404(invoice_id)
    xmr_amount = Decimal(invoice.amount_xmr)
    label = f"Selfdroid Order #{invoice.order_id}"
    payment_uri = gateway.generate_payment_uri(invoice.subaddress, xmr_amount, label)

    qr = qrcode.make(payment_uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


@web_payments_blueprint.route("/payment-webhook", methods=["POST"])
def fl_web_payment_webhook():
    """
    Webhook receiver for external payment confirmation callbacks.

    Expected JSON body:
    {
        "invoice_id": 123,
        "subaddress": "4...",
        "amount_xmr": "0.500000000000",
        "tx_hash": "...",
        "confirmations": 6,
        "status": "confirmed"
    }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    invoice_id = data.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "Missing invoice_id"}), 400

    invoice = PaymentInvoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    invoice.status = data.get("status", invoice.status)
    invoice.confirmations = data.get("confirmations", invoice.confirmations)
    invoice.payment_tx_hash = data.get("tx_hash", invoice.payment_tx_hash)
    db.session.commit()

    return jsonify({"status": "ok", "invoice_id": invoice_id})
