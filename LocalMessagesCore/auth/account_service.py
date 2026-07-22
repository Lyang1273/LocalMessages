import secrets
import threading
import uuid
from datetime import datetime

from .password import hash_password, verify_password
from .repository import AccountRepository

ACCOUNT_STATUS_NORMAL = "正常"
ACCOUNT_STATUS_RESTRICTED = "限制"
ACCOUNT_STATUS_DISABLED = "禁用"
ALLOWED_ACCOUNT_STATUSES = {
    ACCOUNT_STATUS_NORMAL,
    ACCOUNT_STATUS_RESTRICTED,
    ACCOUNT_STATUS_DISABLED,
}
DEFAULT_RESTRICTIONS = {
    "can_send_messages": True,
    "can_receive_messages": True,
}


class AccountService:
    def __init__(self, data_path, max_username_length=20):
        self.repository = AccountRepository(data_path)
        self.max_username_length = max_username_length
        self._tokens = {}
        self._lock = threading.Lock()

    def sign_up(self, username, password):
        username = username.strip()
        self._validate_credentials(username, password)

        with self._lock:
            accounts = self.repository.load_accounts()
            if self._find_by_username(accounts, username):
                raise ValueError("用户名已存在")

            account = {
                "uuid": str(uuid.uuid4()),
                "username": username,
                "password_hash": hash_password(password),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": ACCOUNT_STATUS_NORMAL,
                "restrictions": DEFAULT_RESTRICTIONS.copy(),
                "token": None,
            }
            accounts.append(account)
            self.repository.save_accounts(accounts)
            return self._public_account(account)

    def sign_in(self, username, password):
        username = username.strip()
        if not username or not password:
            raise ValueError("用户名和密码不能为空")

        with self._lock:
            accounts = self.repository.load_accounts()
            account = self._find_by_username(accounts, username)
            if not account or not verify_password(password, account.get("password_hash", "")):
                raise ValueError("用户名或密码错误")
            if account.get("status") == ACCOUNT_STATUS_DISABLED:
                raise PermissionError("此账户在此服务器上已被禁用")

            old_token = account.get("token")
            if old_token:
                self._tokens.pop(old_token, None)

            token = secrets.token_urlsafe(32)
            account["token"] = token
            self._tokens[token] = account["uuid"]
            self.repository.save_accounts(accounts)
            return token, self._public_account(account)

    def logout(self, token):
        if not token:
            return False

        with self._lock:
            accounts = self.repository.load_accounts()
            account = self._find_by_token(accounts, token)
            if not account:
                self._tokens.pop(token, None)
                return False

            account["token"] = None
            self._tokens.pop(token, None)
            self.repository.save_accounts(accounts)
            return True

    def get_account_by_token(self, token):
        if not token:
            return None

        with self._lock:
            accounts = self.repository.load_accounts()
            account = self._find_by_token(accounts, token)
            if not account:
                self._tokens.pop(token, None)
                return None
            if account.get("status") == ACCOUNT_STATUS_DISABLED:
                return None
            return self._public_account(account)

    def set_status(self, username, status):
        if status not in ALLOWED_ACCOUNT_STATUSES:
            raise ValueError("账户状态无效")

        with self._lock:
            accounts = self.repository.load_accounts()
            account = self._find_by_username(accounts, username.strip())
            if not account:
                return False
            account["status"] = status
            if status == ACCOUNT_STATUS_DISABLED and account.get("token"):
                self._tokens.pop(account["token"], None)
                account["token"] = None
            self.repository.save_accounts(accounts)
            return True

    def list_accounts(self):
        with self._lock:
            accounts = self.repository.load_accounts()
            return [self._management_account(account) for account in accounts]

    def get_account(self, username):
        with self._lock:
            account = self._find_by_username(
                self.repository.load_accounts(),
                username.strip(),
            )
            return self._management_account(account) if account else None

    def update_account(self, current_username, username, password, status, restrictions):
        username = username.strip()
        self._validate_username(username)

        if status not in ALLOWED_ACCOUNT_STATUSES:
            raise ValueError("账户状态无效")

        normalized_restrictions = self._normalize_restrictions(restrictions)

        with self._lock:
            accounts = self.repository.load_accounts()
            account = self._find_by_username(accounts, current_username.strip())
            if not account:
                return None

            duplicate = self._find_by_username(accounts, username)
            if duplicate and duplicate is not account:
                raise ValueError("用户名已存在")

            username_changed = account.get("username") != username
            account["username"] = username
            if username_changed and account.get("token"):
                self._tokens.pop(account["token"], None)
                account["token"] = None

            if password:
                if len(password) < 6:
                    raise ValueError("密码至少需要 6 个字符")
                account["password_hash"] = hash_password(password)
                if account.get("token"):
                    self._tokens.pop(account["token"], None)
                    account["token"] = None

            account["status"] = status
            account["restrictions"] = normalized_restrictions
            if status == ACCOUNT_STATUS_DISABLED and account.get("token"):
                self._tokens.pop(account["token"], None)
                account["token"] = None

            self.repository.save_accounts(accounts)
            return self._management_account(account)

    def _validate_credentials(self, username, password):
        self._validate_username(username)
        if not password:
            raise ValueError("密码不能为空")
        if len(password) < 6:
            raise ValueError("密码至少需要 6 个字符")

    def _validate_username(self, username):
        if not username:
            raise ValueError("用户名不能为空")
        if len(username) > self.max_username_length:
            raise ValueError(f"用户名不能超过 {self.max_username_length} 个字符")

    @staticmethod
    def _normalize_restrictions(restrictions):
        restrictions = restrictions or {}
        return {
            "can_send_messages": bool(restrictions.get("can_send_messages", True)),
            "can_receive_messages": bool(restrictions.get("can_receive_messages", True)),
        }

    def _management_account(self, account):
        account.setdefault("restrictions", DEFAULT_RESTRICTIONS.copy())
        public_account = self._public_account(account)
        public_account["password_hash"] = account.get("password_hash", "")
        return public_account

    @staticmethod
    def _find_by_username(accounts, username):
        for account in accounts:
            if account.get("username") == username:
                return account
        return None

    @staticmethod
    def _find_by_token(accounts, token):
        for account in accounts:
            if account.get("token") == token:
                return account
        return None

    @staticmethod
    def _public_account(account):
        return {
            "uuid": account["uuid"],
            "username": account["username"],
            "created_at": account["created_at"],
            "status": account["status"],
            "restrictions": account.get("restrictions", DEFAULT_RESTRICTIONS.copy()),
        }
