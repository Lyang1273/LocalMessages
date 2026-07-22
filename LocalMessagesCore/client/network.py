import json
import threading
import urllib.error
import urllib.parse
import urllib.request

from LocalMessagesCore.protocol import (
    CONNECT_PATH,
    DISCONNECT_PATH,
    EVENT_FORCE_DISCONNECTED,
    EVENT_HEARTBEAT,
    EVENTS_PATH,
    MESSAGES_PATH,
    PROTOCOL_VERSION,
    SIGN_IN_PATH,
    SIGN_UP_PATH,
)


class ApiError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class NetworkClient:
    def __init__(self, on_message, on_close):
        self.base_url = ""
        self.token = None
        self.running = False
        self.on_message = on_message
        self.on_close = on_close
        self._close_notified = False

    def _request(self, method, path, payload=None, timeout=30):
        url = f"{self.base_url}{path}"
        data = None

        headers = {
            "Accept": "application/json",
        }

        if payload is not None:
            data = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_data = response.read()
        except urllib.error.HTTPError as exc:
            try:
                error_data = json.loads(exc.read().decode("utf-8"))
                message = error_data.get("message", str(exc))
            except Exception:
                message = str(exc)

            raise ApiError(message, status_code=exc.code) from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"无法连接服务器：{exc.reason}"
            ) from exc

        if not raw_data:
            return {}

        return json.loads(raw_data.decode("utf-8"))

    def sign_up(self, username, password):
        response = self._request(
            "POST",
            SIGN_UP_PATH,
            {
                "username": username,
                "password": password,
            },
        )
        return response.get("status") == "ok"

    def connect_server(self, host, port):
        self.base_url = f"http://{host}:{port}"
        self._close_notified = False
        return self._request(
            "POST",
            CONNECT_PATH,
            {
                "protocol_version": PROTOCOL_VERSION,
            },
        )

    def sign_in(self, username, password):
        try:
            sign_in_response = self._request(
                "POST",
                SIGN_IN_PATH,
                {
                    "username": username,
                    "password": password,
                },
            )

            if sign_in_response.get("status") != "ok":
                raise ConnectionError(
                    sign_in_response.get(
                        "message",
                        "登录失败",
                    )
                )

            self.token = sign_in_response.get("token")

            if not self.token:
                raise ConnectionError("服务器未返回登录令牌")

            self.running = True

            threading.Thread(
                target=self._receive_loop,
                daemon=True,
            ).start()

            return sign_in_response

        except Exception:
            self._cleanup()
            raise

    def connect(self, host, port, username, password):
        connection_response = self.connect_server(host, port)
        if connection_response.get("status") != "ok":
            raise ConnectionError(
                connection_response.get("message", "服务器拒绝连接")
            )
        self.sign_in(username, password)
        return connection_response

    def send(self, content):
        if not self.running or not self.token:
            return False

        try:
            response = self._request(
                "POST",
                MESSAGES_PATH,
                {
                    "token": self.token,
                    "content": content,
                },
                timeout=10,
            )
            return response.get("status") == "ok"
        except ApiError as exc:
            if exc.status_code in (401, 408, 502, 503, 504):
                self._cleanup()
                self._notify_close()
            return False
        except (ConnectionError, TimeoutError, OSError):
            self._cleanup()
            self._notify_close()
            return False
        except Exception:
            return False

    def _receive_loop(self):
        while self.running and self.token:
            try:
                query = urllib.parse.urlencode({
                    "token": self.token,
                })

                message = self._request(
                    "GET",
                    f"{EVENTS_PATH}?{query}",
                    timeout=35,
                )

                if message.get("type") == EVENT_HEARTBEAT:
                    continue

                self.on_message(message)

                if message.get("type") == EVENT_FORCE_DISCONNECTED:
                    break

            except (
                TimeoutError,
                ConnectionError,
                ApiError,
                OSError,
                ValueError,
            ):
                if self.running:
                    break

        self._cleanup()
        self._notify_close()

    def _notify_close(self):
        if self._close_notified:
            return

        self._close_notified = True

        try:
            self.on_close()
        except Exception:
            pass

    def _cleanup(self):
        self.running = False
        self.token = None

    def disconnect(self):
        token = self.token

        if token:
            try:
                self._request(
                    "POST",
                    DISCONNECT_PATH,
                    {"token": token},
                    timeout=3,
                )
            except Exception:
                pass

        self._cleanup()
