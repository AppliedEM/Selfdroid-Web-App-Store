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
from selfdroid.Constants import Constants
from selfdroid.appstorage.AppStorageHelpers import AppStorageHelpers
from selfdroid.web.endpointbases.WebAtLeastUserEndpointBase import WebAtLeastUserEndpointBase
from selfdroid.EndpointWithAppIDBase import EndpointWithAppIDBase
from selfdroid.appstorage.crud.AppSaleManager import AppSaleManager
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid import db


class PaymentDownloadEndpoint(WebAtLeastUserEndpointBase, EndpointWithAppIDBase):
    def handle_request(self) -> None:
        sale_id = self.app_id_from_url_params
        sale = AppSaleManager.get_by_id(sale_id)

        if sale is None or sale.payment_status != "confirmed":
            self.message_collector.add_error_message("Payment not confirmed. Please complete the payment first.")
            self.redirect_and_finish_request("web_blueprint.fl_web_user_upload_app")
            return

        app_id = sale.app_id
        app = db.session.get(AppMetadataDBModel, app_id)
        if app is None:
            flask.abort(404)

        apk_filename = AppStorageHelpers.get_apk_filename_by_app_id(app_id)
        self.send_file_and_finish_request(Constants.APKS_DIRECTORY,
                                          apk_filename,
                                          f"{app.app_name}.apk",
                                          as_attachment=True)
