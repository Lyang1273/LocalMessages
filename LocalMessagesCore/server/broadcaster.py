import json


class Broadcaster:
    def __init__(self, manager):
        self.manager = manager

    def broadcast(self, message, exclude=None):
        data = (
            json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")

        dead = []

        for sock in self.manager.get_all_sockets():
            if sock == exclude:
                continue

            try:
                sock.sendall(data)
            except OSError:
                dead.append(sock)

        for sock in dead:
            self.manager.remove(sock)