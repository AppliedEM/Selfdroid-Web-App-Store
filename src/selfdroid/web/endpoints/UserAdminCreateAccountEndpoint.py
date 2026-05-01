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
from selfdroid.web.endpointbases.WebAdminEndpointBase import WebAdminEndpointBase
from selfdroid.web.forms.UserAccountForms import UserAdminCreateAccountForm
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager


class UserAdminCreateAccountEndpoint(WebAdminEndpointBase):
    def handle_request(self) -> None:
        create_form = UserAdminCreateAccountForm()
        self.message_collector.register_form("admin_create_account", create_form)

        if create_form.validate_on_submit():
            try:
                user_id = flask.session.get("user_account_id", 1)
                UserAccountManager.create_account(
                    username=create_form.username.data,
                    password=create_form.password.data,
                    created_by_id=user_id,
                )
                self.message_collector.add_success_message(f"Account '{create_form.username.data}' created successfully!")
            except ValueError as e:
                self.message_collector.add_error_message(str(e))

            self.redirect_and_finish_request("web_blueprint.fl_web_admin_user_accounts")

        self.render_template_and_finish_request("admin_user_accounts.html", all_accounts=UserAccountManager.get_all_accounts(), create_form=create_form)
