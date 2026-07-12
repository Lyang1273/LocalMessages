import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime


class ServerWindow:
    def __init__(self, root, server_core, on_close=None):
        self.root = root
        self.server_core = server_core
        self.on_close = on_close

        self.root.title("Local Messages - Ver 0.0.0 - 服务器管理")
        self.root.geometry("800x500")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()

        if self.server_core:
            self.server_core.set_callbacks(
                on_log=self.server_log,
                on_user_list_update=self.update_user_list,
            )

    def _build_ui(self):
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(ctrl_frame, text="停止服务器", command=self.close).pack(side=tk.LEFT, padx=5)

        main_pane = tk.Frame(self.root)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = tk.Frame(main_pane)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left_frame, text="服务器日志").pack(anchor=tk.W)

        self.server_log_text = scrolledtext.ScrolledText(left_frame, state=tk.DISABLED)
        self.server_log_text.pack(fill=tk.BOTH, expand=True)
        self.server_log_text.tag_config("time", foreground="#999999")
        self.server_log_text.tag_config("info", foreground="#000000")
        self.server_log_text.tag_config("success", foreground="#2e7d32")
        self.server_log_text.tag_config("error", foreground="#c62828")

        right_frame = tk.Frame(main_pane, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="在线用户").pack(anchor=tk.W)
        self.user_listbox = tk.Listbox(right_frame)
        self.user_listbox.pack(fill=tk.BOTH, expand=True)

    def server_log(self, msg):
        if self.root.winfo_exists():
            self.root.after(0, lambda: self._server_log_impl(msg))

    def _server_log_impl(self, msg):
        if not self.root.winfo_exists():
            return

        self.server_log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.server_log_text.insert(tk.END, f"[{timestamp}] ", "time")

        if msg.startswith("[+]") or msg.startswith("Server listening"):
            tag = "success"
        elif msg.startswith("[-]") or "error" in msg.lower():
            tag = "error"
        else:
            tag = "info"

        self.server_log_text.insert(tk.END, msg + "\n", tag)
        self.server_log_text.see(tk.END)
        self.server_log_text.config(state=tk.DISABLED)

    def update_user_list(self, users):
        if self.root.winfo_exists():
            self.root.after(0, lambda: self._update_user_list_impl(users))

    def _update_user_list_impl(self, users):
        if not self.root.winfo_exists():
            return

        self.user_listbox.delete(0, tk.END)
        for user in users:
            self.user_listbox.insert(tk.END, user)

    def close(self):
        if self.server_core:
            self.server_core.stop()
        if self.on_close:
            self.on_close()
