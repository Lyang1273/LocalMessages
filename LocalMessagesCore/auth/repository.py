import json
import threading
from pathlib import Path


class AccountRepository:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_unlocked({"accounts": []})

    def load_accounts(self):
        with self._lock:
            return self._read_unlocked().get("accounts", [])

    def save_accounts(self, accounts):
        with self._lock:
            self._write_unlocked({"accounts": accounts})

    def _read_unlocked(self):
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"账户数据文件格式无效：{self.path}") from exc

        if not isinstance(data, dict) or not isinstance(data.get("accounts"), list):
            raise ValueError(f"账户数据文件结构无效：{self.path}")
        return data

    def _write_unlocked(self, data):
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        temp_path.replace(self.path)
