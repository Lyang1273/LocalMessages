"""Shared HTTP protocol constants for LocalMessages clients and servers."""

PROTOCOL_VERSION = 1

CONNECT_PATH = "/api/connect"
SIGN_UP_PATH = "/api/sign_up"
SIGN_IN_PATH = "/api/sign_in"
LOGOUT_PATH = "/api/logout"
MESSAGES_PATH = "/api/messages"
EVENTS_PATH = "/api/events"
DISCONNECT_PATH = "/api/disconnect"
STATUS_PATH = "/api/status"

EVENT_HEARTBEAT = "heartbeat"
EVENT_MESSAGE = "message"
EVENT_USER_JOINED = "user_joined"
EVENT_USER_LEFT = "user_left"
EVENT_FORCE_DISCONNECTED = "force_disconnected"
