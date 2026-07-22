import tkinter as tk
from tkinter import messagebox


class SignUpWindow:
    def __init__(self, parent, network):
        self.parent = parent
        self.network = network

        self.window = tk.Toplevel(parent)
        self.window.title("注册账户")
        self.window.geometry("320x250")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self.window)
        frame.pack(expand=True, padx=24, pady=20)

        tk.Label(frame, text="用户名:").pack(anchor="w")
        self.username_entry = tk.Entry(frame, width=28)
        self.username_entry.pack(pady=(0, 10))

        tk.Label(frame, text="密码:").pack(anchor="w")
        self.password_entry = tk.Entry(frame, width=28, show="*")
        self.password_entry.pack(pady=(0, 10))

        tk.Label(frame, text="确认密码:").pack(anchor="w")
        self.confirm_entry = tk.Entry(frame, width=28, show="*")
        self.confirm_entry.pack(pady=(0, 16))

        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="注册", width=10, command=self._sign_up).pack(side=tk.LEFT)
        tk.Button(button_frame, text="取消", width=10, command=self.window.destroy).pack(side=tk.RIGHT)

        self.username_entry.focus_set()

    def _sign_up(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if not username or not password:
            messagebox.showwarning("输入错误", "请输入用户名和密码。", parent=self.window)
            return
        if password != confirm:
            messagebox.showwarning("输入错误", "两次输入的密码不一致。", parent=self.window)
            return

        try:
            self.network.sign_up(username, password)
        except Exception as exc:
            messagebox.showerror("注册失败", str(exc), parent=self.window)
            return

        messagebox.showinfo("注册成功", "账户已创建，可以登录。", parent=self.window)
        self.window.destroy()
