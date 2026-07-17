import queue
import threading


class ClientManager:
    def __init__(self):
        self._clients = {}
        self._muted_users = set()
        self._lock = threading.Lock()

    def add(self, token, username):
        with self._lock:
            if any(
                client["username"] == username
                for client in self._clients.values()
            ):
                return False

            self._clients[token] = {
                "username": username,
                "events": queue.Queue(),
            }
            return True

    def remove(self, token):
        with self._lock:
            client = self._clients.pop(token, None)

            if client:
                username = client["username"]
                self._muted_users.discard(username)
                return username

            return None

    def get_token(self, username):
        with self._lock:
            for token, client in self._clients.items():
                if client["username"] == username:
                    return token

            return None

    def get_client(self, token):
        with self._lock:
            return self._clients.get(token)

    def mute(self, username):
        with self._lock:
            usernames = {
                client["username"]
                for client in self._clients.values()
            }

            if username not in usernames:
                return False

            self._muted_users.add(username)
            return True

    def unmute(self, username):
        with self._lock:
            if username not in self._muted_users:
                return False

            self._muted_users.remove(username)
            return True

    def is_muted(self, username):
        with self._lock:
            return username in self._muted_users

    def get_users(self):
        with self._lock:
            return [
                client["username"]
                for client in self._clients.values()
            ]

    def get_display_users(self):
        with self._lock:
            return [
                f"[Mute] {client['username']}"
                if client["username"] in self._muted_users
                else client["username"]
                for client in self._clients.values()
            ]

    def get_all_tokens(self):
        with self._lock:
            return list(self._clients.keys())

    def publish(self, token, message):
        client = self.get_client(token)

        if client:
            client["events"].put(message)

    def remove_and_get_events(self, username):
        token = self.get_token(username)

        if not token:
            return None, None

        with self._lock:
            client = self._clients.pop(token, None)

            if not client:
                return None, None

            self._muted_users.discard(username)
            return token, client["events"]