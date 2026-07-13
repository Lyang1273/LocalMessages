import json
import socket
import threading
from datetime import datetime

from .broadcaster import Broadcaster
from .manager import ClientManager


class ChatServerCore:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.manager = ClientManager()
        self.broadcaster = Broadcaster(self.manager)
        self.running = False
        self.server_sock = None
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

    def _send_json(self, sock, message):
        data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        sock.sendall(data)

    def _receive_json(self, sock, recv_buffer):
        while "\n" not in recv_buffer:
            data = sock.recv(4096)

            if not data:
                raise ConnectionError("客户端已断开连接")

            recv_buffer += data.decode("utf-8")

        line, recv_buffer = recv_buffer.split("\n", 1)
        return json.loads(line), recv_buffer

    def _broadcast_server_message(self, content):
        self.broadcaster.broadcast({
            "type": "message",
            "username": "Server",
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    def broadcast_server_message(self, content):
        content = content.strip()

        if not content:
            return False

        self._broadcast_server_message(content)
        self._log(f"[Server] 广播消息：{content}")
        return True

    def start(self):
        self.running = True
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
            self.server_sock.settimeout(1.0)

            self._log(f"Server listening on {self.host}:{self.port}")

            while self.running:
                try:
                    client_sock, address = self.server_sock.accept()
                    client_sock.settimeout(60.0)

                    self._log(
                        f"客户端请求连接：{address[0]}:{address[1]}"
                    )

                    threading.Thread(
                        target=self._handle_client,
                        args=(client_sock,),
                        daemon=True,
                    ).start()

                except socket.timeout:
                    continue
                except OSError:
                    if self.running:
                        raise
                    break
        finally:
            self._cleanup()

    def stop(self):
        self.running = False

        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
            finally:
                self.server_sock = None

        self._log("Server stopped")

    def _cleanup(self):
        self.running = False

        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
            finally:
                self.server_sock = None

    def force_disconnect(self, username):
        sock = self.manager.getout(username)

        if sock is None:
            return False

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            try:
                sock.close()
            except OSError:
                pass

        self._log(f"[-] {username} was forcefully disconnected")
        self._update_users()

        self.broadcaster.broadcast({
            "type": "user_left",
            "username": username,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
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

    def _handle_client(self, sock):
        username = None
        recv_buffer = ""

        try:
            msg, recv_buffer = self._receive_json(sock, recv_buffer)

            if msg.get("type") != "connection_request":
                self._send_json(sock, {
                    "type": "connection_response",
                    "status": "error",
                    "message": "必须先发送连接请求",
                })
                return

            if msg.get("protocol_version") != 1:
                self._send_json(sock, {
                    "type": "connection_response",
                    "status": "error",
                    "message": "不支持的协议版本",
                })
                return

            self._send_json(sock, {
                "type": "connection_response",
                "status": "ok",
                "server_status": "running",
                "protocol_version": 1,
                "online_users": self.manager.get_users(),
                "server_time": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            })

            msg, recv_buffer = self._receive_json(sock, recv_buffer)

            if msg.get("type") != "login":
                self._send_json(sock, {
                    "type": "login_response",
                    "status": "error",
                    "message": "必须发送登录请求",
                })
                return

            username = msg.get("name", "").strip()

            if not username:
                self._send_json(sock, {
                    "type": "login_response",
                    "status": "error",
                    "message": "用户名不能为空",
                })
                username = None
                return

            if username in self.manager.get_users():
                self._send_json(sock, {
                    "type": "login_response",
                    "status": "error",
                    "message": "用户名已存在",
                })
                username = None
                return

            self.manager.add(sock, username)

            self._send_json(sock, {
                "type": "login_response",
                "status": "ok",
                "message": "登录成功",
                "username": username,
                "online_users": self.manager.get_users(),
            })

            self._log(f"[+] {username} connected")
            self._update_users()

            self.broadcaster.broadcast({
                "type": "user_joined",
                "username": username,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "online_users": self.manager.get_users(),
            }, exclude=sock)

            while self.running:
                try:
                    msg, recv_buffer = self._receive_json(sock, recv_buffer)

                    if msg.get("type") != "message":
                        continue

                    content = msg.get("content", "").strip()

                    if not content:
                        continue

                    if self.manager.is_muted(username):
                        self._log(
                            f"[!] 已拦截被禁言用户 {username} 的消息：{content}"
                        )

                        self._send_json(sock, {
                            "type": "message",
                            "username": "Server",
                            "content": "禁言中，消息发送失败",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        })
                        continue

                    self._log(f"[#] {username}: {content}")

                    self.broadcaster.broadcast({
                        "type": "message",
                        "username": username,
                        "content": content,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })

                except socket.timeout:
                    continue
                except (
                    ConnectionError,
                    json.JSONDecodeError,
                    OSError,
                    UnicodeDecodeError,
                ):
                    break

        except socket.timeout:
            self._log("Client connection timed out before login")
        except (
            ConnectionError,
            json.JSONDecodeError,
            OSError,
            UnicodeDecodeError,
        ) as exc:
            self._log(f"Client error: {exc}")

        finally:
            if username:
                removed_username = self.manager.remove(sock)

                if removed_username is not None:
                    self._log(f"[-] {username} disconnected")
                    self._update_users()

                    self.broadcaster.broadcast({
                        "type": "user_left",
                        "username": username,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "online_users": self.manager.get_users(),
                    })

            try:
                sock.close()
            except OSError:
                pass