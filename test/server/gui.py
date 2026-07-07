import tkinter as tk
from tkinter import scrolledtext
from server_core import ChatServerCore
import threading

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("局域网聊天服务器")
        self.root.geometry("600x500")
        self.core = None
        self.running = False

        self.create_widgets()

    def create_widgets(self):
        # 控制面板
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(ctrl_frame, text="端口:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="5000")
        tk.Entry(ctrl_frame, textvariable=self.port_var, width=6).pack(side=tk.LEFT, padx=5)

        self.start_btn = tk.Button(ctrl_frame, text="启动", command=self.start_server,
                                   bg="green", fg="white")
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(ctrl_frame, text="停止", command=self.stop_server,
                                  bg="red", fg="white", state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(ctrl_frame, text="未启动", fg="red")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # 在线用户列表
        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tk.Label(list_frame, text="在线用户:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.user_listbox = tk.Listbox(list_frame, height=6)
        self.user_listbox.pack(fill=tk.BOTH, expand=True)

        # 日志显示
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tk.Label(log_frame, text="服务器日志:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def start_server(self):
        port_str = self.port_var.get().strip()
        try:
            port = int(port_str)
        except ValueError:
            self.log("端口必须是数字")
            return

        self.core = ChatServerCore(host='0.0.0.0', port=port)
        self.core.set_callbacks(
            on_log=self.log,
            on_user_list_update=self.update_user_list
        )
        threading.Thread(target=self.core.start, daemon=True).start()
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="运行中", fg="green")
        self.log(f"服务器启动在端口 {port}")

    def stop_server(self):
        if self.core:
            self.core.stop()
            self.core = None
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="已停止", fg="red")
        self.log("服务器已停止")
        self.update_user_list([])

    def log(self, msg):
        self.root.after(0, lambda: self._log(msg))

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_user_list(self, users):
        self.root.after(0, lambda: self._update_user_list(users))

    def _update_user_list(self, users):
        self.user_listbox.delete(0, tk.END)
        for u in users:
            self.user_listbox.insert(tk.END, u)