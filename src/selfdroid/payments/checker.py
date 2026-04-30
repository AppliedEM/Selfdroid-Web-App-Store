"""
Background payment checker.

Runs as a Flask application thread. Polls monero-wallet-rpc
for payment confirmations on all pending invoices.
"""

import threading
import time
import logging
from decimal import Decimal
from selfdroid import app
from selfdroid.payments.invoice import PaymentInvoice
from selfdroid.payments.gateway import gateway

logger = logging.getLogger(__name__)

# Polling interval in seconds (30s is fine for low-volume)
POLL_INTERVAL = 30
# Minimum received amount before checking confirmations (in XMR)
MIN_CONFIRMATION_THRESHOLD = Decimal("0.000000000001")


class PaymentChecker:
    """Background thread that checks pending payments."""

    def __init__(self):
        self._thread = None
        self._running = False

    def start(self):
        """Start the background checker thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        logger.info("Payment checker started")

    def stop(self):
        """Stop the background checker thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Payment checker stopped")

    def _check_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                with app.app_context():
                    self._check_pending_invoices()
            except Exception as e:
                logger.error(f"Error in payment checker: {e}")
            time.sleep(POLL_INTERVAL)

    def _check_pending_invoices(self):
        """Check all pending invoices for payments."""
        pending = PaymentInvoice.query.filter(
            PaymentInvoice.status.in_(["pending", "confirming"])
        ).all()

        for invoice in pending:
            try:
                if invoice.is_expired():
                    invoice.status = "expired"
                    app.logger.warning(f"Invoice {invoice.order_id} expired")
                    db.session.commit()
                    continue

                expected = Decimal(invoice.amount_xmr)
                result = gateway.check_payment(
                    invoice.subaddress,
                    expected,
                    invoice.required_confirmations,
                )

                if result["status"] == "confirming":
                    invoice.status = "confirming"
                    invoice.confirmations = result["confirmations"]
                elif result["confirmed"]:
                    invoice.status = "confirmed"
                    invoice.confirmations = result["confirmations"]
                    app.logger.info(
                        f"Invoice {invoice.order_id} confirmed: "
                        f"{result['received']} XMR"
                    )
                else:
                    invoice.status = "pending"
                    invoice.confirmations = result["confirmations"]

                db.session.commit()

            except Exception as e:
                app.logger.error(f"Error checking invoice {invoice.order_id}: {e}")
                db.session.rollback()


# Singleton
checker = PaymentChecker()
