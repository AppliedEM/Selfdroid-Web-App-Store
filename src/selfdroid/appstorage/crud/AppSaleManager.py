import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select
from selfdroid import db
from selfdroid.appstorage.AppSaleDBModel import AppSaleDBModel


class AppSaleManager:
    @staticmethod
    def create_sale(app_id: int, buyer_user_id: int, amount_usd: Decimal, amount_xmr: Decimal, currency: str = "usd") -> AppSaleDBModel:
        sale = AppSaleDBModel(
            app_id=app_id,
            buyer_user_id=buyer_user_id,
            amount_usd=amount_usd,
            amount_xmr=amount_xmr,
            currency=currency,
            payment_status="pending",
        )
        db.session.add(sale)
        db.session.commit()
        return sale

    @staticmethod
    def get_by_id(sale_id: int) -> Optional[AppSaleDBModel]:
        return db.session.get(AppSaleDBModel, sale_id)

    @staticmethod
    def get_by_app_and_user(app_id: int, buyer_user_id: int) -> Optional[AppSaleDBModel]:
        stmt = select(AppSaleDBModel).filter_by(
            app_id=app_id,
            buyer_user_id=buyer_user_id,
            payment_status="confirmed",
        ).order_by(AppSaleDBModel.created_at.desc())
        return db.session.execute(stmt).scalar()

    @staticmethod
    def get_pending_by_app_and_user(app_id: int, buyer_user_id: int) -> Optional[AppSaleDBModel]:
        stmt = select(AppSaleDBModel).filter_by(
            app_id=app_id,
            buyer_user_id=buyer_user_id,
            payment_status="pending",
        ).order_by(AppSaleDBModel.created_at.desc())
        return db.session.execute(stmt).scalar()

    @staticmethod
    def confirm_sale(sale_id: int, invoice_id: str = None) -> Optional[AppSaleDBModel]:
        sale = db.session.get(AppSaleDBModel, sale_id)
        if sale is None:
            return None
        sale.payment_status = "confirmed"
        sale.invoice_id = invoice_id
        sale.download_issued_at = datetime.datetime.utcnow()
        db.session.commit()
        return sale

    @staticmethod
    def expire_sale(sale_id: int) -> Optional[AppSaleDBModel]:
        sale = db.session.get(AppSaleDBModel, sale_id)
        if sale is None:
            return None
        sale.payment_status = "expired"
        db.session.commit()
        return sale

    @staticmethod
    def get_pending_sales() -> List[AppSaleDBModel]:
        stmt = select(AppSaleDBModel).filter_by(payment_status="pending").order_by(AppSaleDBModel.created_at.desc())
        return db.session.execute(stmt).scalars().all()

    @staticmethod
    def get_sales_for_user(user_id: int) -> List[AppSaleDBModel]:
        stmt = select(AppSaleDBModel).filter_by(buyer_user_id=user_id).order_by(AppSaleDBModel.created_at.desc())
        return db.session.execute(stmt).scalars().all()
