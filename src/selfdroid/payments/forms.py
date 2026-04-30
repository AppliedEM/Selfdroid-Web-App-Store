"""
WTForms for payment-related forms.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class PaymentCheckoutForm(FlaskForm):
    """Form for creating a Monero payment invoice."""
    order_id = StringField("Order ID", validators=[DataRequired()])
    amount_fiat = DecimalField(
        "Amount (USD)",
        validators=[DataRequired(), NumberRange(min=0.01)],
        places=2,
    )
    currency = SelectField(
        "Currency",
        choices=[("usd", "USD ($)")],
        default="usd",
        validators=[DataRequired()],
    )
    submit = SubmitField("Generate Payment")


class PaymentSettingsForm(FlaskForm):
    """Form for payment gateway configuration."""
    confirmations_required = StringField(
        "Confirmations Required",
        default="2",
        validators=[Optional()],
    )
    invoice_expiry_hours = StringField(
        "Invoice Expiry (hours)",
        default="24",
        validators=[Optional()],
    )
    min_payment_xmr = StringField(
        "Minimum Payment (XMR)",
        default="0.001",
        validators=[Optional()],
    )
    submit = SubmitField("Save Settings")
