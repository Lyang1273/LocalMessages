# ... existing code ...
import tkinter as tk
from tkinter import scrolledtext, Menu
from datetime import datetime


class ChatWindow:
    def __init__(self, root, network, username, on_close=None):
        self.root = root
        self.network = network
        self.username = username
        self.on_close = on_close

        self.root.title("Local Messages - 聊天")
        self.root.geometry("800x500")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()

    def _build_ui(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        menubar.add_command(label="断开", command=self.close)
        menubar.add_command(label="退出", command=self.root.quit)

        self.msg_display = scrolledtext.ScrolledText(self.root)
        self.msg_display.configure(state="disabled")
        self.msg_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        self.msg_display.tag_config("own", foreground="#2196F3")
        self.msg_display.tag_config("other", foreground="#4CAF50")
        self.msg_display.tag_config("system", foreground="#FF9800")
        self.msg_display.tag_config("time", foreground="#999999")

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))

        self.input_text = tk.Text(bottom_frame, height=8)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_text.bind("<Control-Return>", lambda e: self.send_message())

        send_btn = tk.Button(bottom_frame, text="发送", command=self.send_message)
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.input_text.focus_set()

    def send_message(self):
        msg = self.input_text.get("1.0", tk.END).strip()
        if not msg or not self.network:
            return
        if self.network.send(msg):
            self.input_text.delete("1.0", tk.END)

    def handle_message(self, msg):
        typ = msg.get("type")
        if typ == "message":
            self.show_message(
                msg["username"],
                msg["content"],
                msg["timestamp"],
                msg["username"] == self.username
            )
        elif typ == "user_joined":
            self.show_system(f"✓ {msg['username']} 加入了聊天", msg["timestamp"])
        elif typ == "user_left":
            self.show_system(f"✗ {msg['username']} 离开了聊天", msg["timestamp"])

    def show_message(self, username, content, timestamp, is_own):
        self.msg_display.config(state=tk.NORMAL)
        self.msg_display.insert(tk.END, f"[{timestamp}] ", "time")
        self.msg_display.insert(tk.END, f"{username}: ", "own" if is_own else "other")
        self.msg_display.insert(tk.END, f"{content}\n")
        self.msg_display.see(tk.END)
        self.msg_display.config(state=tk.DISABLED)

    def show_system(self, text, timestamp=None):
        ts = timestamp or datetime.now().strftime("%H:%M:%S")
        self.msg_display.config(state=tk.NORMAL)
        self.msg_display.insert(tk.END, f"[{ts}] ", "time")
        self.msg_display.insert(tk.END, f"{text}\n", "system")
        self.msg_display.see(tk.END)
        self.msg_display.config(state=tk.DISABLED)

    def close(self):
        if self.network:
            self.network.disconnect()
        if self.on_close:
            self.on_close()
        self.root.destroy()
# ... existing code ...
