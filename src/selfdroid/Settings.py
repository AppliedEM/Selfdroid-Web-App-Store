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


from typing import Optional
import os.path
from selfdroid.Helpers import Helpers


class Settings:
    DATA_DIRECTORY: str = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../app_data/")

    # This string will be displayed in the web app's title.
    INSTANCE_NAME: str = "Selfdroid Dev"

    # Date & time in the web app will be formatted according to this format string.
    DATETIME_DISPLAY_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # The timezone in which the date & time will be displayed in the web app. Can be either None, in which case the
    #  server's timezone will be used, or a zoneinfo timezone name, e.g. "Europe/Prague" or "America/New_York".
    DISPLAY_TIMEZONE: Optional[str] = None

    # If you're using a production web server (e.g. nginx), you'll also need to change the maximum upload size in its config file
    MAX_UPLOAD_SIZE: int = 64 * 1024 * 1024  # 64 MiB

    # The session cookie is discarded when a client's browsing session ends, so the login lifetime doesn't have to be long.
    WEB_LOGIN_LIFETIME: int = 10800  # in seconds; 3 hours

    # Set this to current date and time if you want to invalidate all past logged in sessions (which you should do when changing passwords).
    MINIMUM_WEB_LOGIN_TIMESTAMP: int = Helpers.sql_datetime_to_unix_timestamp("2021-07-22 12:00:00")

    @staticmethod
    def get_user_password_hash() -> Optional[str]:
        """
        This function returns the user password hashed using bcrypt.
        If the function returns None, clients won't be required to enter a password (all clients will be allowed to access the app as users).
        """

        # The password hash can be fetched e.g. from environment variables, database, properly protected file, ...
        # For development, use a default hash if no password is configured.
        # To set your own password, generate a hash with: python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
        import os
        env_hash = os.environ.get("SELFDROID_USER_PASSWORD_HASH")
        if env_hash:
            return env_hash
        return None  # Passwordless user login for dev

    @staticmethod
    def get_admin_password_hash() -> str:
        """
        This function returns the admin password hashed using bcrypt.
        """

        # The password hash can be fetched e.g. from environment variables, a database, a properly protected file, ...
        import os
        env_hash = os.environ.get("SELFDROID_ADMIN_PASSWORD_HASH")
        if env_hash:
            return env_hash
        # Default dev password: admin123
        import bcrypt
        return bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()

    # User upload settings
    USER_UPLOAD_ENABLED: bool = os.environ.get("SELFDROID_USER_UPLOAD_ENABLED", "true").lower() in ("true", "1", "yes")
    USER_UPLOAD_REQUIRES_APPROVAL: bool = os.environ.get("SELFDROID_USER_UPLOAD_REQUIRES_APPROVAL", "true").lower() in ("true", "1", "yes")

    @staticmethod
    def get_min_price_usd():
        import os
        env_val = os.environ.get("SELFDROID_MIN_PRICE_USD")
        if env_val:
            from decimal import Decimal
            return Decimal(env_val)
        return Decimal("0.01")

    @staticmethod
    def get_min_price_xmr():
        import os
        env_val = os.environ.get("SELFDROID_MIN_PRICE_XMR")
        if env_val:
            from decimal import Decimal
            return Decimal(env_val)
        return Decimal("0.001")

    DOWNLOAD_EXPIRY_HOURS: int = int(os.environ.get("SELFDROID_DOWNLOAD_EXPIRY_HOURS", "24"))
