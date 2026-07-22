import json


class Broadcaster:
    def __init__(self, manager, can_receive=None):
        self.manager = manager
        self.can_receive = can_receive

    def broadcast(self, message, exclude=None):
        for token in self.manager.get_all_tokens():
            if token == exclude:
                continue
            if self.can_receive and not self.can_receive(token):
                continue

            self.manager.publish(token, message)
