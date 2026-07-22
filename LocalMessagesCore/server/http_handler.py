import json
import queue
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from LocalMessagesCore.protocol import (
    CONNECT_PATH,
    DISCONNECT_PATH,
    EVENT_HEARTBEAT,
    EVENT_MESSAGE,
    EVENTS_PATH,
    LOGOUT_PATH,
    MESSAGES_PATH,
    PROTOCOL_VERSION,
    SIGN_IN_PATH,
    SIGN_UP_PATH,
    STATUS_PATH,
)


def create_request_handler(server_core):
    """Build an HTTP handler bound to one ChatServerCore instance."""

    class RequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send_json(self, payload, status=200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("无效的请求长度") from exc

            if content_length > 1024 * 1024:
                raise ValueError("请求数据过大")

            raw_body = self.rfile.read(content_length)
            return json.loads(raw_body.decode("utf-8")) if raw_body else {}

        def _token_from_query(self):
            values = parse_qs(urlparse(self.path).query).get("token", [])
            return values[0] if values else None

        def do_GET(self):
            path = urlparse(self.path).path
            if path == STATUS_PATH:
                self._send_status()
            elif path == EVENTS_PATH:
                self._get_event()
            else:
                self._send_json({"status": "error", "message": "接口不存在"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
                if path == CONNECT_PATH:
                    self._connect(payload)
                elif path == SIGN_UP_PATH:
                    self._sign_up(payload)
                elif path == SIGN_IN_PATH:
                    self._sign_in(payload)
                elif path == LOGOUT_PATH:
                    self._logout(payload)
                elif path == MESSAGES_PATH:
                    self._message(payload)
                elif path == DISCONNECT_PATH:
                    self._disconnect(payload)
                else:
                    self._send_json({"status": "error", "message": "接口不存在"}, 404)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"status": "error", "message": str(exc)}, 400)
            except Exception as exc:
                server_core._log(f"HTTP 请求处理失败：{exc}")
                self._send_json({"status": "error", "message": "服务器内部错误"}, 500)

        def _send_status(self):
            self._send_json({
                "status": "ok",
                "data": {
                    "server": {
                        "name": server_core.server_name,
                        "version": "0.0.0",
                        "running": server_core.running,
                        "host": server_core.host,
                        "port": server_core.port,
                        "start_time": server_core.start_time,
                    },
                    "protocol": {
                        "version": PROTOCOL_VERSION,
                        "heartbeat_timeout": server_core.heartbeat_timeout,
                        "max_wait_time": server_core.heartbeat_timeout + 10,
                    },
                    "users": {
                        "online": len(server_core.manager.get_users()),
                        "list": server_core.manager.get_users(),
                        "muted": server_core.manager.get_muted_users(),
                    },
                    "limits": {
                        "max_users": server_core.max_users,
                        "max_message_length": server_core.max_message_length,
                        "max_username_length": server_core.max_username_length,
                    },
                },
            })

        def _get_event(self):
            client = server_core.manager.get_client(self._token_from_query())
            if not client:
                self._send_json({"status": "error", "message": "连接已失效"}, 401)
                return

            if not server_core.account_service.get_account_by_token(self._token_from_query()):
                server_core.chat_service.disconnect(self._token_from_query())
                self._send_json({"status": "error", "message": "登录已失效"}, 401)
                return

            try:
                event = client["events"].get(timeout=server_core.heartbeat_timeout)
            except queue.Empty:
                event = {"type": EVENT_HEARTBEAT}
            self._send_json(event)

        def _connect(self, payload):
            if payload.get("protocol_version") != PROTOCOL_VERSION:
                self._send_json({"type": "connection_response", "status": "error", "message": "不支持的协议版本"}, 400)
                return

            self._send_json({
                "type": "connection_response",
                "status": "ok",
                "server_status": "running",
                "protocol_version": PROTOCOL_VERSION,
                "online_users": server_core.manager.get_users(),
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        def _sign_up(self, payload):
            try:
                account = server_core.account_service.sign_up(
                    payload.get("username", ""),
                    payload.get("password", ""),
                )
            except ValueError as exc:
                self._send_json({"status": "error", "message": str(exc)}, 400)
                return

            self._send_json({"status": "ok", "account": account})

        def _sign_in(self, payload):
            username = payload.get("username", payload.get("name", "")).strip()
            password = payload.get("password", "")
            if not username or not password:
                self._send_json({"type": "login_response", "status": "error", "message": "用户名不能为空"}, 400)
                return
            if len(username) > server_core.max_username_length:
                self._send_json({"type": "login_response", "status": "error", "message": f"用户名不能超过 {server_core.max_username_length} 个字符"}, 400)
                return

            try:
                token, account = server_core.account_service.sign_in(username, password)
            except PermissionError as exc:
                self._send_json({"type": "login_response", "status": "error", "message": str(exc)}, 403)
                return
            except ValueError as exc:
                self._send_json({"type": "login_response", "status": "error", "message": str(exc)}, 401)
                return

            success, message = server_core.chat_service.sign_in(token, username)
            if not success:
                server_core.account_service.logout(token)
                self._send_json({"type": "login_response", "status": "error", "message": message}, 409)
                return
            self._send_json({"type": "login_response", "status": "ok", "message": "登录成功", "token": token, "account": account, "username": username, "online_users": server_core.manager.get_users()})

        def _logout(self, payload):
            token = payload.get("token")
            server_core.chat_service.disconnect(token)
            server_core.account_service.logout(token)
            self._send_json({"status": "ok"})

        def _message(self, payload):
            token = payload.get("token")
            account = server_core.account_service.get_account_by_token(token)
            if not account:
                self._send_json({"status": "error", "message": "登录已失效"}, 401)
                return

            if (
                account.get("status") == "限制"
                and not account.get("restrictions", {}).get("can_send_messages", True)
            ):
                client = server_core.manager.get_client(token)
                if client:
                    server_core.manager.publish(token, {
                        "type": EVENT_MESSAGE,
                        "username": "Server",
                        "content": "账户限制中，无法发言",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })
                    server_core._log(
                        f"[!] 已拦截受限用户 {client['username']} 的消息"
                    )
                self._send_json({"status": "ok"})
                return

            success, message, status = server_core.chat_service.send_message(
                token, payload.get("content", ""),
            )
            if success:
                self._send_json({"status": "ok"})
            else:
                self._send_json({"status": "error", "message": message}, status)

        def _disconnect(self, payload):
            token = payload.get("token")
            server_core.chat_service.disconnect(token)
            server_core.account_service.logout(token)
            self._send_json({"status": "ok"})

        def log_message(self, format_string, *args):
            return

    return RequestHandler
