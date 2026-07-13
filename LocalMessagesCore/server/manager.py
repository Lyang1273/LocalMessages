import threading


class ClientManager:
    def __init__(self):
        self._clients = {}  # socket -> username
        self._muted_users = set()
        self._lock = threading.Lock()

    def add(self, sock, username):
        with self._lock:
            self._clients[sock] = username

    def remove(self, sock):
        with self._lock:
            username = self._clients.pop(sock, None)

            if username is not None:
                self._muted_users.discard(username)

            return username

    def getout(self, username):
        with self._lock:
            for sock, client_name in list(self._clients.items()):
                if client_name == username:
                    del self._clients[sock]
                    self._muted_users.discard(username)
                    return sock

        return None

    def mute(self, username):
        with self._lock:
            if username not in self._clients.values():
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
            return list(self._clients.values())

    def get_display_users(self):
        with self._lock:
            return [
                f"[Mute] {username}"
                if username in self._muted_users
                else username
                for username in self._clients.values()
            ]

    def get_all_sockets(self):
        with self._lock:
            return list(self._clients.keys())