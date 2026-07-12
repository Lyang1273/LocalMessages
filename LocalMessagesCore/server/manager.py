import threading


class ClientManager:
    def __init__(self):
        self._clients = {}  # socket -> username
        self._lock = threading.Lock()

    def add(self, sock, username):
        with self._lock:
            self._clients[sock] = username

    def remove(self, sock):
        with self._lock:
            return self._clients.pop(sock, None)

    def getout(self, username):
        with self._lock:
            for sock, client_name in list(self._clients.items()):
                if client_name == username:
                    del self._clients[sock]
                    return sock
        return None

    def get_users(self):
        with self._lock:
            return list(self._clients.values())

    def get_all_sockets(self):
        with self._lock:
            return list(self._clients.keys())
