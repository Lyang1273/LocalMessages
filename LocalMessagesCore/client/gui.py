import tkinter as tk
from tkinter import messagebox, scrolledtext, Menu
from datetime import datetime
from network import NetworkClient


class ChatGUI:
    def __init__(self):
        # 主窗口（登录窗口）
        self.root = tk.Tk()
        self.root.title("局域网聊天")
        self.root.geometry("400x350")
        self.root.resizable(False, False)
        self.network = None
        self.username = ""
        self.chat_window = None

        self._setup_login()

        # 主窗口关闭时退出程序
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    # ---------- 登录界面 ----------
    def _setup_login(self):
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack(expand=True, padx=30, pady=30)

        tk.Label(self.login_frame, text="局域网聊天", font=("Arial", 18, "bold")).pack(pady=10)

        tk.Label(self.login_frame, text="服务器:").pack(anchor='w')
        self.server_entry = tk.Entry(self.login_frame, width=30)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(pady=(0, 10))

        tk.Label(self.login_frame, text="端口:").pack(anchor='w')
        self.port_entry = tk.Entry(self.login_frame, width=30)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(pady=(0, 10))

        tk.Label(self.login_frame, text="用户名:").pack(anchor='w')
        self.name_entry = tk.Entry(self.login_frame, width=30)
        self.name_entry.pack(pady=(0, 15))

        tk.Button(self.login_frame, text="连接", command=self._do_connect, width=15).pack()
        self.status_label = tk.Label(self.login_frame, text="未连接", fg="red")
        self.status_label.pack(pady=5)

    def _do_connect(self):
        host = self.server_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("错误", "端口必须是数字")
            return
        username = self.name_entry.get().strip()
        if not username:
            messagebox.showerror("错误", "请输入用户名")
            return

        self.network = NetworkClient(
            on_message=self._on_network_message,
            on_close=self._on_network_close
        )
        try:
            self.network.connect(host, port, username)
            self.username = username
            # 隐藏登录窗口
            self.root.withdraw()
            # 创建聊天窗口
            self._create_chat_window()
        except Exception as e:
            messagebox.showerror("连接失败", str(e))
            self.network = None

    # ---------- 聊天窗口（独立 Toplevel） ----------
    def _create_chat_window(self):
        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("Local Messages")
        self.chat_window.geometry("800x500")
        self.chat_window.protocol("WM_DELETE_WINDOW", self._disconnect)

        # 菜单栏
        menubar = Menu(self.chat_window)
        self.chat_window.config(menu=menubar)
        menubar.add_command(label="断开", command=self._disconnect)
        menubar.add_command(label="退出", command=self._quit)

        # 消息显示区
        self.msg_display = scrolledtext.ScrolledText(self.chat_window)
        self.msg_display.configure(state="disabled")
        self.msg_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        # 颜色标签
        self.msg_display.tag_config("own", foreground="#2196F3")
        self.msg_display.tag_config("other", foreground="#4CAF50")
        self.msg_display.tag_config("system", foreground="#FF9800")
        self.msg_display.tag_config("time", foreground="#999999")

        # 底部输入区域
        bottom_frame = tk.Frame(self.chat_window)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))

        self.input_text = tk.Text(bottom_frame, height=8)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_text.bind("<Control-Return>", lambda e: self._send_message())

        send_btn = tk.Button(bottom_frame, text="发送", command=self._send_message)
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # 窗口创建完成后，将焦点设置到输入框
        self.input_text.focus_set()

    # ---------- 网络回调 ----------
    def _on_network_message(self, msg):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.after(0, lambda: self._handle_message(msg))

    def _on_network_close(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.after(0, self._disconnect)

    def _handle_message(self, msg):
        typ = msg.get('type')
        if typ == 'message':
            self._show_message(msg['username'], msg['content'],
                               msg['timestamp'], msg['username'] == self.username)
        elif typ == 'user_joined':
            self._show_system(f"✓ {msg['username']} 加入了聊天", msg['timestamp'])
        elif typ == 'user_left':
            self._show_system(f"✗ {msg['username']} 离开了聊天", msg['timestamp'])

    def _show_message(self, username, content, timestamp, is_own):
        self.msg_display.config(state=tk.NORMAL)
        self.msg_display.insert(tk.END, f"[{timestamp}] ", "time")
        self.msg_display.insert(tk.END, f"{username}: ", "own" if is_own else "other")
        self.msg_display.insert(tk.END, f"{content}\n")
        self.msg_display.see(tk.END)
        self.msg_display.config(state=tk.DISABLED)

    def _show_system(self, text, timestamp=None):
        ts = timestamp or datetime.now().strftime('%H:%M:%S')
        self.msg_display.config(state=tk.NORMAL)
        self.msg_display.insert(tk.END, f"[{ts}] ", "time")
        self.msg_display.insert(tk.END, f"{text}\n", "system")
        self.msg_display.see(tk.END)
        self.msg_display.config(state=tk.DISABLED)

    # ---------- 用户操作 ----------
    def _send_message(self):
        msg = self.input_text.get("1.0", tk.END).strip()
        if not msg or not self.network:
            return
        if self.network.send(msg):
            self.input_text.delete("1.0", tk.END)

    def _disconnect(self):
        if self.network:
            self.network.disconnect()
            self.network = None
        # 关闭聊天窗口
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.destroy()
            self.chat_window = None
        # 显示登录窗口
        self.root.deiconify()
        self.status_label.config(text="已断开", fg="red")

    def _quit(self):
        if self.network:
            self.network.disconnect()
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.destroy()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
