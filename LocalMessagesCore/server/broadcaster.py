import json


class Broadcaster:
    def __init__(self, manager):
        self.manager = manager

    def broadcast(self, message, exclude=None):
        for token in self.manager.get_all_tokens():
            if token == exclude:
                continue

            self.manager.publish(token, message)