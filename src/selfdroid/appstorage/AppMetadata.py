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


from __future__ import annotations
from typing import Optional, Dict, Union, List
import datetime
import dateutil.tz
from selfdroid.Settings import Settings
from selfdroid.appstorage.AppStorageHelpers import AppStorageHelpers
from selfdroid.appstorage.AppMetadataDBModel import AppMetadataDBModel


class AppMetadata:
    """
    A class containing the metadata fetched from the database along with some auxiliary properties and methods.

    AppMetadataDBModel should be used only when working with the database; in every other case, this class should be used instead.
    """

    def __init__(self, db_model: AppMetadataDBModel):
        self.id: int = db_model.id

        self.app_name: str = db_model.app_name
        self.package_name: str = db_model.package_name
        self.version_code: int = db_model.version_code
        self.version_name: str = db_model.version_name

        self.min_api_level: int = db_model.min_api_level
        self.max_api_level: Optional[int] = db_model.max_api_level

        self.apk_file_size: int = db_model.apk_file_size

        # User upload & pricing
        self.uploaded_by: Optional[int] = db_model.uploaded_by
        self.owner_username: Optional[str] = db_model.owner_username
        self.price_usd: Optional[float] = float(db_model.price_usd) if db_model.price_usd is not None else None
        self.price_xmr: Optional[float] = float(db_model.price_xmr) if db_model.price_xmr is not None else None
        self.currency: Optional[str] = db_model.currency
        self.is_published: bool = db_model.is_published
        self.is_approved: bool = db_model.is_approved
        self.approved_by: Optional[int] = db_model.approved_by
        self.approved_at: Optional[datetime.datetime] = self._add_utc_timezone_to_naive_datetime_object(db_model.approved_at) if db_model.approved_at else None
        self.rejection_reason: Optional[str] = db_model.rejection_reason

        self.added_datetime: datetime.datetime = self._add_utc_timezone_to_naive_datetime_object(db_model.added_datetime)
        self.last_updated_datetime: datetime.datetime = self._add_utc_timezone_to_naive_datetime_object(db_model.last_updated_datetime)

        self.added_datetime_timezoned: datetime.datetime = self._add_display_timezone_to_utc_datetime_object(self.added_datetime)
        self.last_updated_datetime_timezoned: datetime.datetime = self._add_display_timezone_to_utc_datetime_object(self.last_updated_datetime)

    @classmethod
    def from_db_model(cls, db_model: AppMetadataDBModel) -> AppMetadata:
        # Wrapper method future expansion
        return cls(db_model)

    def _add_utc_timezone_to_naive_datetime_object(self, datetime_object: datetime.datetime) -> datetime.datetime:
        return datetime_object.replace(tzinfo=dateutil.tz.tzutc())

    def _add_display_timezone_to_utc_datetime_object(self, datetime_object: datetime.datetime) -> datetime.datetime:
        display_timezone = dateutil.tz.tzlocal() if (Settings.DISPLAY_TIMEZONE is None) else dateutil.tz.gettz(Settings.DISPLAY_TIMEZONE)

        return datetime_object.astimezone(tz=display_timezone)

    @property
    def is_free(self) -> bool:
        return self.price_usd is None or float(self.price_usd) == 0

    def to_api_dict(self) -> Dict[str, Union[str, int, float, bool, None]]:
        return {
            "id": self.id,

            "app_name": self.app_name,
            "package_name": self.package_name,
            "version_code": self.version_code,
            "version_name": self.version_name,

            "min_api_level": self.min_api_level,
            "max_api_level": self.max_api_level,

            "apk_file_size": self.apk_file_size,

            "added_timestamp": int(self.added_datetime.timestamp()),
            "last_updated_timestamp": int(self.last_updated_datetime.timestamp()),

            # User upload & pricing
            "uploaded_by": self.uploaded_by,
            "owner_username": self.owner_username,
            "owner_user_id": self.uploaded_by,
            "price_usd": self.price_usd,
            "price_xmr": self.price_xmr,
            "currency": self.currency,
            "is_published": self.is_published,
            "is_approved": self.is_approved,
            "is_free": self.is_free,
        }

    def get_apk_path(self) -> str:
        return AppStorageHelpers.get_apk_path_by_app_id(self.id)

    def get_apk_filename(self) -> str:
        return AppStorageHelpers.get_apk_filename_by_app_id(self.id)

    def get_icon_path(self) -> str:
        return AppStorageHelpers.get_icon_path_by_app_id(self.id)

    def get_icon_filename(self) -> str:
        return AppStorageHelpers.get_icon_filename_by_app_id(self.id)

    def get_apk_download_name(self) -> str:
        return "{}.apk".format(self.app_name)

    def get_icon_download_name(self) -> str:
        return "{}.png".format(self.app_name)
