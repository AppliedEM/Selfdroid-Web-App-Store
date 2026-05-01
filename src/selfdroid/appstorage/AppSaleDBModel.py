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


import datetime
from decimal import Decimal
from selfdroid import db


class AppSaleDBModel(db.Model):
    __tablename__ = "app_sale"
    __table_args__ = {"sqlite_autoincrement": True}

    id = db.Column(db.Integer(), primary_key=True, nullable=False)
    app_id = db.Column(db.Integer(), db.ForeignKey("app_metadata.id"), nullable=False)
    buyer_user_id = db.Column(db.Integer(), db.ForeignKey("user_account.id"), nullable=False)
    amount_usd = db.Column(db.Numeric(10, 2), nullable=False)
    amount_xmr = db.Column(db.Numeric(20, 12), nullable=False)
    currency = db.Column(db.String(3), default="usd", nullable=False)
    payment_status = db.Column(db.String(16), default="pending", nullable=False)
    invoice_id = db.Column(db.String(64), nullable=True)
    download_issued_at = db.Column(db.DateTime(), nullable=True)
    created_at = db.Column(db.DateTime(), default=datetime.datetime.utcnow, nullable=False)

    def is_expired(self):
        if self.download_issued_at:
            expiry = self.download_issued_at + datetime.timedelta(hours=24)
            return datetime.datetime.utcnow() > expiry
        return False

    def to_dict(self):
        return {
            "id": self.id,
            "app_id": self.app_id,
            "buyer_user_id": self.buyer_user_id,
            "amount_usd": str(self.amount_usd),
            "amount_xmr": str(self.amount_xmr),
            "currency": self.currency,
            "payment_status": self.payment_status,
            "invoice_id": self.invoice_id,
            "download_issued_at": self.download_issued_at.strftime("%Y-%m-%d %H:%M:%S") if self.download_issued_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "is_expired": self.is_expired(),
        }
