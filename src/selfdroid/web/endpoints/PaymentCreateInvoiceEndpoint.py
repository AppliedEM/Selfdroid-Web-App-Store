# SPDX-License-Identifier: BSD-3-Clause
#
# Copyright (c) 2021 Vít Labuda. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#  1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#     disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#     following disclaimer in the documentation and/or other materials provided with the distribution.
#  3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
#     products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from typing import Dict, Any
import flask
from decimal import Decimal
from selfdroid.web.endpointbases.WebAtLeastUserEndpointBase import WebAtLeastUserEndpointBase
from selfdroid.EndpointWithAppIDBase import EndpointWithAppIDBase
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.crud.AppSaleManager import AppSaleManager
from selfdroid.payments.gateway import MoneroGateway, MoneroPaymentError
from selfdroid import db


class PaymentCreateInvoiceEndpoint(WebAtLeastUserEndpointBase, EndpointWithAppIDBase):
    def handle_request(self) -> None:
        app_id = self.app_id_from_url_params
        app = db.session.get(AppMetadataDBModel, app_id)
        if app is None:
            flask.abort(404)

        if app.is_free:
            self.message_collector.add_error_message("This app is free. You can download it directly.")
            self.redirect_and_finish_request("web_blueprint.fl_web_app_details", app_id=app_id)
            return

        user_id = flask.session.get("user_account_id", None)
        if user_id is None:
            self.redirect_and_finish_request("web_blueprint.fl_web_login")
            return

        # If the user already has a confirmed sale for this app, skip
        # invoicing and go straight to download.
        confirmed_sale = AppSaleManager.get_by_app_and_user(app_id, user_id)
        if confirmed_sale:
            self.redirect_and_finish_request("web_blueprint.fl_web_payment_download", app_id=confirmed_sale.id)
            return

        # If a pending sale already exists for this app+user, re-show it
        # instead of creating a new one (and a new subaddress).
        existing_sale = AppSaleManager.get_pending_by_app_and_user(app_id, user_id)
        if existing_sale and existing_sale.invoice_id:
            gateway = MoneroGateway()
            self.render_template_and_finish_request(
                "payment_page.html",
                sale=existing_sale,
                subaddress=existing_sale.invoice_id,
                amount_xmr=float(existing_sale.amount_xmr),
                amount_usd=float(existing_sale.amount_usd),
                app=app,
                payment_uri=gateway.generate_payment_uri(
                    existing_sale.invoice_id,
                    existing_sale.amount_xmr,
                    label=f"App purchase: {app.app_name}",
                ),
            )

        amount_usd = float(app.price_usd) if app.price_usd else 0
        amount_xmr = float(app.price_xmr) if app.price_xmr else 0

        gateway = MoneroGateway()

        if amount_xmr == 0:
            try:
                amount_xmr = float(gateway.fiat_to_xmr(Decimal(str(amount_usd))))
            except MoneroPaymentError:
                self.message_collector.add_error_message("Failed to calculate XMR amount. Please try again.")
                self.redirect_and_finish_request("web_blueprint.fl_web_app_details", app_id=app_id)
                return

        sale = AppSaleManager.create_sale(
            app_id=app_id,
            buyer_user_id=user_id,
            amount_usd=Decimal(str(amount_usd)),
            amount_xmr=Decimal(str(amount_xmr)),
            currency=app.currency or "xmr",
        )

        subaddress, _ = gateway.create_invoice_address(label=f"App purchase: {app.app_name} (sale #{sale.id})")
        sale.invoice_id = subaddress
        db.session.commit()

        self.render_template_and_finish_request(
            "payment_page.html",
            sale=sale,
            subaddress=subaddress,
            amount_xmr=amount_xmr,
            amount_usd=amount_usd,
            app=app,
            payment_uri=gateway.generate_payment_uri(subaddress, Decimal(str(amount_xmr)), label=f"App purchase: {app.app_name}"),
        )
