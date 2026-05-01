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
import os
import tempfile
import flask
from decimal import Decimal
from sqlalchemy import select
from selfdroid.web.endpointbases.WebAtLeastUserEndpointBase import WebAtLeastUserEndpointBase
from selfdroid.web.forms.UserUploadAppForm import UserUploadAppForm
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel
from selfdroid.appstorage.crud.AppAdder import AppAdder
from selfdroid.appstorage.AppStorageHelpers import AppStorageHelpers
from selfdroid.appstorage.crud.AppGetter import AppGetter
from selfdroid.appstorage.crud.AppAdderException import AppAdderException
from selfdroid import db


class UserUploadAppEndpoint(WebAtLeastUserEndpointBase):
    def handle_request(self) -> None:
        upload_form = UserUploadAppForm()
        self.message_collector.register_form("user_upload", upload_form)

        if upload_form.validate_on_submit():
            self._perform_upload(upload_form)
            self.redirect_and_finish_request("web_blueprint.fl_web_user_upload_app")

        self.render_template_and_finish_request("web_user_upload.html", upload_form=upload_form)

    def _perform_upload(self, upload_form: UserUploadAppForm) -> None:
        user_id = flask.session.get("user_account_id", None)
        username = flask.session.get("user_account_username", None)

        apk_file = upload_form.apk_file.data
        if apk_file is None:
            self.message_collector.add_error_message("No APK file selected!")
            return

        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as temp_file:
            apk_file.save(temp_file.name)
            temp_apk_path = temp_file.name

        try:
            with AppStorageHelpers.get_app_storage_lock():
                # Check for duplicate package name
                parsed_apk = __import__("selfdroid.appstorage.apk.APKParser", fromlist=["APKParser"]).APKParser(temp_apk_path).parsed_apk
                stmt = select(AppMetadataDBModel).filter_by(package_name=parsed_apk.package_name)
                duplicate = db.session.execute(stmt).scalar()
                if duplicate is not None:
                    self.message_collector.add_error_message(f"An app with package name '{parsed_apk.package_name}' already exists!")
                    return

                # Create the app_metadata row
                price_usd = upload_form.price.data if upload_form.price.data is not None else None
                price_xmr = None
                currency = upload_form.currency.data or "usd"

                if currency == "xmr" and price_usd is not None:
                    from selfdroid.payments.gateway import gateway
                    try:
                        price_xmr = float(gateway.fiat_to_xmr(Decimal(str(price_usd))))
                    except Exception:
                        price_xmr = None

                if currency == "usd" and price_usd is not None:
                    price_xmr = None

                db_model = AppMetadataDBModel(
                    app_name=parsed_apk.app_name,
                    package_name=parsed_apk.package_name,
                    version_code=parsed_apk.version_code,
                    version_name=parsed_apk.version_name,
                    min_api_level=parsed_apk.min_api_level,
                    max_api_level=parsed_apk.max_api_level,
                    apk_file_size=parsed_apk.apk_file_size,
                    uploaded_by=user_id,
                    owner_username=username,
                    price_usd=Decimal(str(price_usd)) if price_usd is not None else None,
                    price_xmr=Decimal(str(price_xmr)) if price_xmr is not None else None,
                    currency=currency,
                    is_published=False,
                    is_approved=False,
                )
                db.session.add(db_model)
                db.session.commit()

                app_id = db_model.id

                # Save APK
                apk_path = AppStorageHelpers.get_apk_path_by_app_id(app_id)
                os.rename(temp_apk_path, apk_path)

                # Save icon
                icon_path = AppStorageHelpers.get_icon_path_by_app_id(app_id)
                with open(icon_path, "wb") as icon_file:
                    icon_file.write(parsed_apk.uniform_png_app_icon)

        except AppAdderException as e:
            db.session.rollback()
            self.message_collector.add_error_message(str(e))
            return
        except Exception as e:
            db.session.rollback()
            self.message_collector.add_error_message("An error occurred while uploading the app!")
            return

        self.message_collector.add_success_message("App uploaded successfully! It is pending admin approval.")
