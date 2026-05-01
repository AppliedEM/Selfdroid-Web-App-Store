import bcrypt
from typing import Optional, List
from selfdroid import db
from selfdroid.appstorage.UserAccountDBModel import UserAccountDBModel


class UserAccountManager:
    @staticmethod
    def create_account(username: str, password: str, created_by_id: int) -> UserAccountDBModel:
        existing = UserAccountDBModel.query.filter_by(username=username).first()
        if existing is not None:
            raise ValueError(f"Username '{username}' is already taken!")

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        account = UserAccountDBModel(
            username=username,
            password_hash=password_hash,
            created_by=created_by_id,
        )
        db.session.add(account)
        db.session.commit()
        return account

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[UserAccountDBModel]:
        account = UserAccountDBModel.query.filter_by(username=username).first()
        if account is None:
            return None
        if not account.is_active:
            return None

        try:
            encoded_password = password.encode("utf-8")
            encoded_hash = account.password_hash.encode("utf-8")
        except UnicodeError:
            return None

        if not bcrypt.checkpw(encoded_password, encoded_hash):
            return None

        return account

    @staticmethod
    def get_by_id(user_id: int) -> Optional[UserAccountDBModel]:
        return UserAccountDBModel.query.get(user_id)

    @staticmethod
    def get_by_username(username: str) -> Optional[UserAccountDBModel]:
        return UserAccountDBModel.query.filter_by(username=username).first()

    @staticmethod
    def get_all_accounts() -> List[UserAccountDBModel]:
        return UserAccountDBModel.query.order_by(UserAccountDBModel.created_at.desc()).all()

    @staticmethod
    def deactivate_account(account_id: int) -> bool:
        account = UserAccountDBModel.query.get(account_id)
        if account is None:
            return False
        account.is_active = False
        db.session.commit()

        apps = db.session.query(UserAccountDBModel).filter_by(owner_username=account.username).all()
        for app in apps:
            app.owner_username = None
            app.uploaded_by = None

        db.session.commit()
        return True

    @staticmethod
    def reset_password(account_id: int, new_password: str) -> bool:
        account = UserAccountDBModel.query.get(account_id)
        if account is None:
            return False

        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        account.password_hash = password_hash
        db.session.commit()
        return True

    @staticmethod
    def delete_account(account_id: int) -> bool:
        account = UserAccountDBModel.query.get(account_id)
        if account is None:
            return False

        username = account.username
        db.session.delete(account)
        db.session.commit()

        apps = db.session.query(UserAccountDBModel).filter_by(owner_username=username).all()
        for app in apps:
            db.session.delete(app)
        db.session.commit()
        return True

    @staticmethod
    def change_password_for_self(account_id: int, old_password: str, new_password: str) -> bool:
        account = UserAccountDBModel.query.get(account_id)
        if account is None:
            return False

        try:
            encoded_old = old_password.encode("utf-8")
            encoded_hash = account.password_hash.encode("utf-8")
        except UnicodeError:
            return False

        if not bcrypt.checkpw(encoded_old, encoded_hash):
            return False

        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        account.password_hash = new_hash
        db.session.commit()
        return True
