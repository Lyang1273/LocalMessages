import socket
import threading
import json


class NetworkClient:
    def __init__(self, on_message, on_close):
        self.sock = None
        self.running = False
        self.on_message = on_message
        self.on_close = on_close
        self._recv_buffer = ""

    def _send_json(self, message):
        data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        self.sock.sendall(data)

    def _receive_json(self):
        while "\n" not in self._recv_buffer:
            data = self.sock.recv(4096)
            if not data:
                raise ConnectionError("服务器已关闭连接")
            self._recv_buffer += data.decode("utf-8")

        line, self._recv_buffer = self._recv_buffer.split("\n", 1)
        return json.loads(line)

    def connect(self, host, port, username):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock.settimeout(30.0)

            # 第一阶段：请求建立应用层连接
            self._send_json({
                "type": "connection_request",
                "protocol_version": 1,
            })

            # 等待服务器返回状态
            server_response = self._receive_json()

            if server_response.get("type") != "connection_response":
                raise ConnectionError("服务器返回了无效的连接响应")

            if server_response.get("status") != "ok":
                raise ConnectionError(
                    server_response.get("message", "服务器拒绝连接")
                )

            # 第二阶段：发送登录请求
            self._send_json({
                "type": "login",
                "name": username,
            })

            # 等待服务器确认登录结果
            login_response = self._receive_json()

            if login_response.get("type") != "login_response":
                raise ConnectionError("服务器返回无效的登录响应")

            if login_response.get("status") != "ok":
                raise ConnectionError(
                    login_response.get("message", "登录失败")
                )

            # 只有服务器确认登录成功后，才进入聊天状态
            self.running = True
            threading.Thread(
                target=self._receive_loop,
                daemon=True,
            ).start()

            return server_response

        except Exception as exc:
            self._cleanup()
            raise exc

    def send(self, content):
        if not self.running or not self.sock:
            return False

        try:
            self._send_json({
                "type": "message",
                "content": content,
            })
            return True
        except OSError:
            self._cleanup()
            return False

    def _receive_loop(self):
        while self.running:
            try:
                msg = self._receive_json()
                self.on_message(msg)
            except socket.timeout:
                continue
            except Exception:
                break

        self._cleanup()
        self.on_close()

    def _cleanup(self):
        self.running = False

        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            finally:
                self.sock = None

    def disconnect(self):
        self._cleanup()