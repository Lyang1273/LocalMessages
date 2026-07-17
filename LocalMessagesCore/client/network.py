import json
import threading
import urllib.error
import urllib.parse
import urllib.request


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

            raise ConnectionError(message) from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"无法连接服务器：{exc.reason}"
            ) from exc

        if not raw_data:
            return {}

        return json.loads(raw_data.decode("utf-8"))

    def connect(self, host, port, username):
        self.base_url = f"http://{host}:{port}"
        self._close_notified = False

        try:
            connection_response = self._request(
                "POST",
                "/api/connect",
                {
                    "protocol_version": 1,
                },
            )

            if connection_response.get("status") != "ok":
                raise ConnectionError(
                    connection_response.get(
                        "message",
                        "服务器拒绝连接",
                    )
                )

            self.token = connection_response.get("token")

            if not self.token:
                raise ConnectionError("服务器未返回连接令牌")

            login_response = self._request(
                "POST",
                "/api/login",
                {
                    "token": self.token,
                    "name": username,
                },
            )

            if login_response.get("status") != "ok":
                raise ConnectionError(
                    login_response.get(
                        "message",
                        "登录失败",
                    )
                )

            self.running = True

            threading.Thread(
                target=self._receive_loop,
                daemon=True,
            ).start()

            return connection_response

        except Exception:
            self._cleanup()
            raise

    def send(self, content):
        if not self.running or not self.token:
            return False

        try:
            response = self._request(
                "POST",
                "/api/messages",
                {
                    "token": self.token,
                    "content": content,
                },
                timeout=10,
            )
            return response.get("status") == "ok"
        except Exception:
            self._cleanup()
            self._notify_close()
            return False

    def _receive_loop(self):
        while self.running and self.token:
            try:
                query = urllib.parse.urlencode({
                    "token": self.token,
                })

                message = self._request(
                    "GET",
                    f"/api/events?{query}",
                    timeout=35,
                )

                if message.get("type") == "heartbeat":
                    continue

                self.on_message(message)

                if message.get("type") == "force_disconnected":
                    break

            except (
                TimeoutError,
                ConnectionError,
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
                    "/api/disconnect",
                    {"token": token},
                    timeout=3,
                )
            except Exception:
                pass

        self._cleanup()