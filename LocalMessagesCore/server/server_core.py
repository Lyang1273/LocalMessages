import json
import queue
import secrets
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .broadcaster import Broadcaster
from .manager import ClientManager


class ChatServerCore:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.manager = ClientManager()
        self.broadcaster = Broadcaster(self.manager)
        self.running = False
        self.server = None
        self._callbacks = {
            "on_log": None,
            "on_user_list_update": None,
        }

    def set_callbacks(self, on_log=None, on_user_list_update=None):
        self._callbacks["on_log"] = on_log
        self._callbacks["on_user_list_update"] = on_user_list_update

    def _log(self, message):
        callback = self._callbacks.get("on_log")

        if callback:
            callback(message)

    def _update_users(self):
        callback = self._callbacks.get("on_user_list_update")

        if callback:
            callback(self.manager.get_display_users())

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")

    def _broadcast_server_message(self, content):
        self.broadcaster.broadcast({
            "type": "message",
            "username": "Server",
            "content": content,
            "timestamp": self._timestamp(),
        })

    def broadcast_server_message(self, content):
        content = content.strip()

        if not content:
            return False

        self._broadcast_server_message(content)
        self._log(f"[Server] 广播消息：{content}")
        return True

    def start(self):
        if self.running:
            return

        self.running = True
        server_core = self

        class RequestHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _send_json(self, payload, status=200):
                body = json.dumps(
                    payload,
                    ensure_ascii=False,
                ).encode("utf-8")

                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(body)),
                )
                self.send_header(
                    "Connection",
                    "close",
                )
                self.end_headers()
                self.wfile.write(body)

            def _read_json(self):
                try:
                    content_length = int(
                        self.headers.get("Content-Length", "0")
                    )
                except ValueError:
                    raise ValueError("无效的请求长度")

                if content_length > 1024 * 1024:
                    raise ValueError("请求数据过大")

                raw_body = self.rfile.read(content_length)

                if not raw_body:
                    return {}

                return json.loads(raw_body.decode("utf-8"))

            def _token_from_query(self):
                query = parse_qs(urlparse(self.path).query)
                values = query.get("token", [])
                return values[0] if values else None

            def do_POST(self):
                path = urlparse(self.path).path

                try:
                    payload = self._read_json()

                    if path == "/api/connect":
                        self._connect(payload)
                    elif path == "/api/login":
                        self._login(payload)
                    elif path == "/api/messages":
                        self._message(payload)
                    elif path == "/api/disconnect":
                        self._disconnect(payload)
                    else:
                        self._send_json(
                            {"status": "error", "message": "接口不存在"},
                            404,
                        )
                except (ValueError, json.JSONDecodeError) as exc:
                    self._send_json(
                        {"status": "error", "message": str(exc)},
                        400,
                    )
                except Exception as exc:
                    server_core._log(f"HTTP 请求处理失败：{exc}")
                    self._send_json(
                        {"status": "error", "message": "服务器内部错误"},
                        500,
                    )

            def do_GET(self):
                path = urlparse(self.path).path

                if path != "/api/events":
                    self._send_json(
                        {"status": "error", "message": "接口不存在"},
                        404,
                    )
                    return

                token = self._token_from_query()
                client = server_core.manager.get_client(token)

                if not client:
                    self._send_json(
                        {
                            "status": "error",
                            "message": "连接已失效",
                        },
                        401,
                    )
                    return

                try:
                    event = client["events"].get(timeout=25)
                except queue.Empty:
                    event = {"type": "heartbeat"}

                self._send_json(event)

            def _connect(self, payload):
                if payload.get("protocol_version") != 1:
                    self._send_json(
                        {
                            "type": "connection_response",
                            "status": "error",
                            "message": "不支持的协议版本",
                        },
                        400,
                    )
                    return

                token = secrets.token_urlsafe(32)

                self._send_json({
                    "type": "connection_response",
                    "status": "ok",
                    "server_status": "running",
                    "protocol_version": 1,
                    "token": token,
                    "online_users": server_core.manager.get_users(),
                    "server_time": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                })

            def _login(self, payload):
                token = payload.get("token")
                username = payload.get("name", "").strip()

                if not token or not username:
                    self._send_json(
                        {
                            "type": "login_response",
                            "status": "error",
                            "message": "用户名不能为空",
                        },
                        400,
                    )
                    return

                if not server_core.manager.add(token, username):
                    self._send_json(
                        {
                            "type": "login_response",
                            "status": "error",
                            "message": "用户名已存在",
                        },
                        409,
                    )
                    return

                self._send_json({
                    "type": "login_response",
                    "status": "ok",
                    "message": "登录成功",
                    "username": username,
                    "online_users": server_core.manager.get_users(),
                })

                server_core._log(f"[+] {username} connected")
                server_core._update_users()

                server_core.broadcaster.broadcast(
                    {
                        "type": "user_joined",
                        "username": username,
                        "timestamp": server_core._timestamp(),
                        "online_users": server_core.manager.get_users(),
                    },
                    exclude=token,
                )

            def _message(self, payload):
                token = payload.get("token")
                client = server_core.manager.get_client(token)

                if not client:
                    self._send_json(
                        {
                            "status": "error",
                            "message": "连接已失效",
                        },
                        401,
                    )
                    return

                content = payload.get("content", "").strip()

                if not content:
                    self._send_json(
                        {"status": "error", "message": "消息不能为空"},
                        400,
                    )
                    return

                username = client["username"]

                if server_core.manager.is_muted(username):
                    server_core._log(
                        f"[!] 已拦截被禁言用户 {username} 的消息：{content}"
                    )
                    server_core.manager.publish(token, {
                        "type": "message",
                        "username": "Server",
                        "content": "禁言中，消息发送失败",
                        "timestamp": server_core._timestamp(),
                    })
                    self._send_json({"status": "ok"})
                    return

                server_core._log(f"[#] {username}: {content}")

                server_core.broadcaster.broadcast({
                    "type": "message",
                    "username": username,
                    "content": content,
                    "timestamp": server_core._timestamp(),
                })

                self._send_json({"status": "ok"})

            def _disconnect(self, payload):
                token = payload.get("token")

                username = server_core.manager.remove(token)

                if username:
                    server_core._log(f"[-] {username} disconnected")
                    server_core._update_users()
                    server_core.broadcaster.broadcast({
                        "type": "user_left",
                        "username": username,
                        "timestamp": server_core._timestamp(),
                        "online_users": server_core.manager.get_users(),
                    })

                self._send_json({"status": "ok"})

            def log_message(self, format_string, *args):
                return

        self.server = ThreadingHTTPServer(
            (self.host, self.port),
            RequestHandler,
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

    def force_disconnect(self, username):
        token, events = self.manager.remove_and_get_events(username)

        if not token:
            return False

        events.put({
            "type": "force_disconnected",
            "username": username,
            "content": "你已被服务器强制下线",
            "timestamp": self._timestamp(),
        })

        self._log(f"[-] {username} was forcefully disconnected")
        self._update_users()

        self.broadcaster.broadcast({
            "type": "user_left",
            "username": username,
            "timestamp": self._timestamp(),
            "online_users": self.manager.get_users(),
        })

        return True

    def mute_user(self, username):
        if not self.manager.mute(username):
            return False

        self._log(f"[!] {username} was muted")
        self._update_users()
        self._broadcast_server_message(f"{username} 被禁言")
        return True

    def unmute_user(self, username):
        if not self.manager.unmute(username):
            return False

        self._log(f"[+] {username} was unmuted")
        self._update_users()
        self._broadcast_server_message(f"{username} 已解除禁言")
        return True

    def is_user_muted(self, username):
        return self.manager.is_muted(username)