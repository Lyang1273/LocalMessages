from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path

from LocalMessagesCore.auth import AccountService

from .broadcaster import Broadcaster
from .chat_service import ChatService
from .http_handler import create_request_handler
from .manager import ClientManager


class ChatServerCore:
    """Coordinates server lifecycle, configuration, and GUI callbacks."""

    def __init__(self, host="0.0.0.0", port=5000, config=None):
        self.host = host
        self.port = port
        self.config = config or {}
        self.max_users = self.config.get("max_users", 100)
        self.max_message_length = self.config.get("max_message_length", 10000)
        self.max_username_length = self.config.get("max_username_length", 20)
        self.heartbeat_timeout = self.config.get("heartbeat_timeout", 25)
        self.server_name = self.config.get("server_name", "LocalMessages")
        self.enable_logging = self.config.get("enable_logging", True)
        self.account_data_path = self.config.get(
            "account_data_path",
            str(Path("data") / f"accounts_{self.port}.json"),
        )

        self.account_service = AccountService(
            self.account_data_path,
            max_username_length=self.max_username_length,
        )
        self.manager = ClientManager(max_users=self.max_users)
        self.broadcaster = Broadcaster(self.manager, can_receive=self._can_receive_messages)
        self.running = False
        self.server = None
        self.start_time = None
        self._callbacks = {"on_log": None, "on_user_list_update": None}
        self.chat_service = ChatService(
            self.manager,
            self.broadcaster,
            self.max_message_length,
            self._log,
            self._update_users,
        )

    def set_callbacks(self, on_log=None, on_user_list_update=None):
        self._callbacks["on_log"] = on_log
        self._callbacks["on_user_list_update"] = on_user_list_update

    def _log(self, message):
        callback = self._callbacks["on_log"]
        if self.enable_logging and callback:
            callback(message)

    def _update_users(self):
        callback = self._callbacks["on_user_list_update"]
        if callback:
            callback(self.manager.get_display_users())

    def _can_receive_messages(self, token):
        account = self.account_service.get_account_by_token(token)
        if not account:
            return False
        if account.get("status") != "限制":
            return True
        return account.get("restrictions", {}).get("can_receive_messages", True)

    def start(self):
        if self.running:
            return

        self.running = True
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.server = ThreadingHTTPServer(
            (self.host, self.port),
            create_request_handler(self),
        )
        self._log(f"HTTP server listening on {self.host}:{self.port}")

        try:
            self.server.serve_forever(poll_interval=0.5)
        finally:
            self.server.server_close()
            self.server = None
            self.running = False

    def stop(self):
        self.running = False
        if self.server:
            self.server.shutdown()
        self._log("HTTP server stopped")

    def broadcast_server_message(self, content):
        return self.chat_service.broadcast_server_message(content)

    def force_disconnect(self, username):
        return self.chat_service.force_disconnect(username)

    def mute_user(self, username):
        return self.chat_service.mute_user(username)

    def unmute_user(self, username):
        return self.chat_service.unmute_user(username)

    def is_user_muted(self, username):
        return self.manager.is_muted(username)

    def list_accounts(self):
        return self.account_service.list_accounts()

    def set_account_status(self, username, status):
        updated = self.account_service.set_status(username, status)
        if status == "禁用":
            self.force_disconnect(username)
        return updated

    def get_account(self, username):
        return self.account_service.get_account(username)

    def update_account(self, current_username, username, password, status, restrictions):
        account = self.account_service.update_account(
            current_username,
            username,
            password,
            status,
            restrictions,
        )
        if account and (current_username != username or password or status == "禁用"):
            self.force_disconnect(current_username)
        return account
