import socket
import threading
import json
from datetime import datetime
from .manager import ClientManager
from .broadcaster import Broadcaster


class ChatServerCore:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.manager = ClientManager()
        self.broadcaster = Broadcaster(self.manager)
        self.running = False
        self.server_sock = None
        self._callbacks = {
            'on_log': None,
            'on_user_list_update': None
        }

    def set_callbacks(self, on_log=None, on_user_list_update=None):
        self._callbacks['on_log'] = on_log
        self._callbacks['on_user_list_update'] = on_user_list_update

    def _log(self, msg):
        cb = self._callbacks.get('on_log')
        if cb:
            cb(msg)

    def _update_users(self):
        cb = self._callbacks.get('on_user_list_update')
        if cb:
            cb(self.manager.get_users())

    def start(self):
        self.running = True
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)
        self._log(f"Server listening on {self.host}:{self.port}")

        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
                client_sock.settimeout(60.0)
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break
        self._cleanup()

    def _handle_client(self, sock):
        username = None
        try:
            data = sock.recv(1024).decode()
            msg = json.loads(data)
            if msg.get('type') != 'login':
                return
            username = msg['name']
            self.manager.add(sock, username)
            self._log(f"[+] {username} connected")
            self._update_users()

            self.broadcaster.broadcast({
                'type': 'user_joined',
                'username': username,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'online_users': self.manager.get_users()
            })

            while self.running:
                try:
                    data = sock.recv(1024).decode()
                    if not data:
                        break
                    msg = json.loads(data)
                    if msg.get('type') == 'message':
                        self._log(f"[#] {username}: {msg['content']}")
                        self.broadcaster.broadcast({
                            'type': 'message',
                            'username': username,
                            'content': msg['content'],
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                except (socket.timeout, json.JSONDecodeError):
                    continue
                except OSError:
                    break
        except Exception as e:
            self._log(f"Client error: {e}")
        finally:
            if username:
                self.manager.remove(sock)
                self._log(f"[-] {username} disconnected")
                self._update_users()
                self.broadcaster.broadcast({
                    'type': 'user_left',
                    'username': username,
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'online_users': self.manager.get_users()
                })
            sock.close()

    def _cleanup(self):
        self.running = False
        if self.server_sock:
            self.server_sock.close()

    def stop(self):
        self.running = False
        if self.server_sock:
            self.server_sock.close()
