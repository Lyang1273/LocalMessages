from datetime import datetime

from LocalMessagesCore.protocol import (
    EVENT_FORCE_DISCONNECTED,
    EVENT_MESSAGE,
    EVENT_USER_JOINED,
    EVENT_USER_LEFT,
)


class ChatService:
    """Owns chat business rules independently of the HTTP transport."""

    def __init__(self, manager, broadcaster, max_message_length, log, update_users):
        self.manager = manager
        self.broadcaster = broadcaster
        self.max_message_length = max_message_length
        self._log = log
        self._update_users = update_users

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")

    def sign_in(self, token, username):
        old_token, old_events = self.manager.remove_and_get_events(username)
        if old_token and old_events:
            old_events.put({
                "type": EVENT_FORCE_DISCONNECTED,
                "username": username,
                "content": "你的账户已在其他地方登录",
                "timestamp": self._timestamp(),
            })

        if not self.manager.add(token, username):
            return False, "用户名已存在或用户数已达上限"

        self._log(f"[+] {username} connected")
        self._update_users()
        self.broadcaster.broadcast({
            "type": EVENT_USER_JOINED,
            "username": username,
            "timestamp": self._timestamp(),
            "online_users": self.manager.get_users(),
        }, exclude=token)
        return True, None

    def send_message(self, token, content):
        client = self.manager.get_client(token)
        if not client:
            return False, "连接已失效", 401

        content = content.strip()
        if not content:
            return False, "消息不能为空", 400

        if len(content) > self.max_message_length:
            return False, "消息过长", 400

        username = client["username"]
        if self.manager.is_muted(username):
            self._log(f"[!] 已拦截被禁言用户 {username} 的消息：{content}")
            self.manager.publish(token, {
                "type": EVENT_MESSAGE,
                "username": "Server",
                "content": "禁言中，消息发送失败",
                "timestamp": self._timestamp(),
            })
            return True, None, 200

        self._log(f"[#] {username}: {content}")
        self.broadcaster.broadcast({
            "type": EVENT_MESSAGE,
            "username": username,
            "content": content,
            "timestamp": self._timestamp(),
        })
        return True, None, 200

    def disconnect(self, token):
        username = self.manager.remove(token)
        if not username:
            return False

        self._log(f"[-] {username} disconnected")
        self._update_users()
        self.broadcaster.broadcast({
            "type": EVENT_USER_LEFT,
            "username": username,
            "timestamp": self._timestamp(),
            "online_users": self.manager.get_users(),
        })
        return True

    def force_disconnect(self, username):
        token, events = self.manager.remove_and_get_events(username)
        if not token:
            return False

        events.put({
            "type": EVENT_FORCE_DISCONNECTED,
            "username": username,
            "content": "你已被服务器强制下线",
            "timestamp": self._timestamp(),
        })
        self._log(f"[-] {username} was forcefully disconnected")
        self._update_users()
        self.broadcaster.broadcast({
            "type": EVENT_USER_LEFT,
            "username": username,
            "timestamp": self._timestamp(),
            "online_users": self.manager.get_users(),
        })
        return True

    def mute_user(self, username):
        if not self.manager.mute(username):
            return False

        self._log(f"[!] {username} was muted")
        self._update_users()
        self.broadcast_server_message(f"{username} 被禁言")
        return True

    def unmute_user(self, username):
        if not self.manager.unmute(username):
            return False

        self._log(f"[+] {username} was unmuted")
        self._update_users()
        self.broadcast_server_message(f"{username} 已解除禁言")
        return True

    def broadcast_server_message(self, content):
        content = content.strip()
        if not content:
            return False

        self.broadcaster.broadcast({
            "type": EVENT_MESSAGE,
            "username": "Server",
            "content": content,
            "timestamp": self._timestamp(),
        })
        self._log(f"[Server] 广播消息：{content}")
        return True
