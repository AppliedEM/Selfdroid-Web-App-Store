"""
Monero payment module for Selfdroid.

Initializes the payment gateway, registers the Flask blueprint,
and starts the background payment checker.
"""

import logging
from flask import Blueprint
from selfdroid.payments.endpoints import web_payments_blueprint
from selfdroid.payments.checker import checker

logger = logging.getLogger(__name__)


def init_payments(app):
    """Initialize the payment module with the Flask app."""
    app.register_blueprint(web_payments_blueprint)
    checker.start()
    logger.info("Monero payment module initialized")

    return app
