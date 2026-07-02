import socket
import json
import threading


class P2pMessages:
    @classmethod
    def sendMessages(cls, ip, port, msg):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, port))

            data = json.dumps({"msg": msg})

            sock.send(data.encode("utf-8"))
            sock.close()
            return True
        except Exception as e:
            return False, str(e)
