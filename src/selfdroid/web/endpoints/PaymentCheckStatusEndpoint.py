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
from selfdroid.web.endpointbases.WebAtLeastUserEndpointBase import WebAtLeastUserEndpointBase
from selfdroid.EndpointWithAppIDBase import EndpointWithAppIDBase
from selfdroid.appstorage.crud.AppSaleManager import AppSaleManager
from selfdroid.payments.gateway import MoneroGateway


class PaymentCheckStatusEndpoint(WebAtLeastUserEndpointBase, EndpointWithAppIDBase):
    def handle_request(self) -> None:
        sale_id = self.app_id_from_url_params
        sale = AppSaleManager.get_by_id(sale_id)
        if sale is None:
            return self.jsonify_and_finish_request({"status": "error", "message": "Sale not found"})

        if sale.payment_status != "pending":
            return self.jsonify_and_finish_request({"status": sale.payment_status})

        if not sale.invoice_id:
            return self.jsonify_and_finish_request({"status": "pending"})

        gateway = MoneroGateway()

        try:
            payment_result = gateway.check_payment(
                address=sale.invoice_id,
                expected_amount_xmr=sale.amount_xmr,
                min_confirmations=2,
            )

            if payment_result["confirmed"]:
                AppSaleManager.confirm_sale(sale_id, invoice_id=sale.invoice_id)
                return self.jsonify_and_finish_request({"status": "confirmed"})

            return self.jsonify_and_finish_request({
                "status": "pending",
                "confirmations": payment_result["confirmations"],
                "required": payment_result["required"],
                "received": str(payment_result["received"]),
            })

        except Exception:
            return self.jsonify_and_finish_request({"status": "pending"})
