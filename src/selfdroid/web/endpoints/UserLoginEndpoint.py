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


import flask
from selfdroid.UserReadableException import UserReadableException
from selfdroid.web.endpointbases.WebPublicOnlyEndpointBase import WebPublicOnlyEndpointBase
from selfdroid.web.forms.UserAccountForms import UserAccountLoginForm
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel
from selfdroid.appstorage.crud.UserAccountManager import UserAccountManager
from sqlalchemy import select


class UserLoginEndpoint(WebPublicOnlyEndpointBase):
    def handle_request(self) -> None:
        login_form = UserAccountLoginForm()
        self.message_collector.register_form("user_login", login_form)

        if login_form.validate_on_submit():
            self._perform_login(login_form)
            self.redirect_and_finish_request("web_blueprint.fl_web_index")

        self.render_template_and_finish_request("web_user_login.html", login_form=login_form)

    def _perform_login(self, login_form: UserAccountLoginForm) -> None:
        username = login_form.username.data
        password = login_form.password.data

        account = UserAccountManager.authenticate(username, password)
        if account is None:
            self.message_collector.add_error_message("Invalid username or password!")
            return

        self.authenticator.log_in_as_user_account(account.id, account.username)
