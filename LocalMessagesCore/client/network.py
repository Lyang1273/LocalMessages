import socket
import threading
import json


class NetworkClient:
    def __init__(self, on_message, on_close):
        self.sock = None
        self.running = False
        self.on_message = on_message
        self.on_close = on_close

    def connect(self, host, port, username):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.sock.settimeout(30.0)
            login = {'type': 'login', 'name': username}
            self.sock.sendall(json.dumps(login, ensure_ascii=False).encode())
            self.running = True
            threading.Thread(target=self._receive_loop, daemon=True).start()
            return True
        except Exception as e:
            self._cleanup()
            raise e

    def send(self, content):
        if not self.running or not self.sock:
            return False
        try:
            msg = {'type': 'message', 'content': content}
            self.sock.sendall(json.dumps(msg, ensure_ascii=False).encode())
            return True
        except:
            self._cleanup()
            return False

    def _receive_loop(self):
        while self.running:
            try:
                data = self.sock.recv(1024).decode()
                if not data:
                    break
                msg = json.loads(data)
                self.on_message(msg)
            except socket.timeout:
                continue
            except:
                break
        self._cleanup()
        self.on_close()

    def _cleanup(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def disconnect(self):
        self._cleanup()
