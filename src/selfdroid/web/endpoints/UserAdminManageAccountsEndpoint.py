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
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager


class UserAdminManageAccountsEndpoint(WebAdminEndpointBase):
    def handle_request(self) -> None:
        action = flask.request.args.get("action")
        account_id = flask.request.args.get("account_id", type=int)

        if action == "deactivate" and account_id:
            UserAccountManager.deactivate_account(account_id)
            self.message_collector.add_success_message("Account deactivated.")

        elif action == "activate" and account_id:
            account = UserAccountDBModel.query.get(account_id)
            if account:
                account.is_active = True
                from selfdroid import db
                db.session.commit()
                self.message_collector.add_success_message("Account activated.")

        elif action == "reset_password" and account_id:
            new_password = flask.request.form.get("new_password", "")
            if new_password and len(new_password) >= 8:
                UserAccountManager.reset_password(account_id, new_password)
                self.message_collector.add_success_message("Password reset successfully.")
            else:
                self.message_collector.add_error_message("Password must be at least 8 characters.")

        elif action == "delete" and account_id:
            UserAccountManager.delete_account(account_id)
            self.message_collector.add_success_message("Account deleted along with all associated apps.")

        all_accounts = UserAccountManager.get_all_accounts()
        self.render_template_and_finish_request("admin_user_accounts.html", all_accounts=all_accounts)
