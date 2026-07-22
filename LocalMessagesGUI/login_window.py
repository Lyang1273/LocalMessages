import tkinter as tk
from tkinter import messagebox

from .register_window import SignUpWindow


class SignInWindow:
    def __init__(self, parent, network, on_sign_in, on_cancel=None):
        self.parent = parent
        self.network = network
        self.on_sign_in = on_sign_in
        self.on_cancel = on_cancel

        self.window = tk.Toplevel(parent)
        self.window.title("账户登录")
        self.window.geometry("320x210")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self.window)
        frame.pack(expand=True, padx=24, pady=5)

        tk.Label(frame, text="用户名:").pack(anchor="w")
        self.username_entry = tk.Entry(frame, width=28)
        self.username_entry.pack(pady=(0, 10))

        tk.Label(frame, text="密码:").pack(anchor="w")
        self.password_entry = tk.Entry(frame, width=28, show="*")
        self.password_entry.pack(pady=(0, 16))

        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x")

        tk.Button(button_frame, text="登录", width=10, command=self._sign_in).pack(side="top")
        tk.Button(button_frame, text="注册一个在此服务器的账户", relief="flat", fg="blue", command=self._open_sign_up).pack(side="bottom", pady=(20, 0))

        self.username_entry.focus_set()

    def _sign_in(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning("输入错误", "请输入用户名和密码。", parent=self.window)
            return

        try:
            response = self.network.sign_in(username, password)
        except Exception as exc:
            messagebox.showerror("登录失败", str(exc), parent=self.window)
            return

        account = response.get("account", {})
        if account.get("status") == "限制":
            restrictions = account.get("restrictions", {})
            can_send = "允许" if restrictions.get("can_send_messages", True) else "禁止"
            can_receive = "允许" if restrictions.get("can_receive_messages", True) else "禁止"
            messagebox.showinfo(
                "账户限制",
                f"此账户当前处于限制状态。\n发言：{can_send}\n查看消息：{can_receive}",
                parent=self.window,
            )

        self.window.destroy()
        self.on_sign_in(username)

    def _open_sign_up(self):
        SignUpWindow(self.window, self.network)

    def _cancel(self):
        self.window.destroy()
        if self.on_cancel:
            self.on_cancel()
