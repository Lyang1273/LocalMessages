import tkinter as tk
from tkinter import messagebox, ttk


class AccountListWindow:
    def __init__(self, parent, server_core):
        self.parent = parent
        self.server_core = server_core
        self.account_usernames = []

        self.window = tk.Toplevel(parent)
        self.window.title("账户管理")
        self.window.geometry("350x250")
        self.window.transient(parent)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        ctrl_frame = tk.Frame(self.window)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=8)

        # tk.Button(ctrl_frame, text="刷新", command=self.refresh).pack(side=tk.LEFT)

        self.account_listbox = tk.Listbox(self.window, selectmode=tk.SINGLE)
        self.account_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.account_listbox.bind("<Double-Button-1>", self._open_selected_account)

    def refresh(self):
        self.account_listbox.delete(0, tk.END)
        self.account_usernames = []
        for account in self.server_core.list_accounts():
            self.account_usernames.append(account["username"])
            self.account_listbox.insert(
                tk.END,
                f"{account['username']} ({account['uuid']})",
            )

    def _open_selected_account(self, event):
        selection = self.account_listbox.curselection()
        if not selection:
            return
        username = self.account_usernames[selection[0]]
        AccountSettingsWindow(self.window, self.server_core, username, self.refresh)


class AccountSettingsWindow:
    def __init__(self, parent, server_core, username, on_saved=None):
        self.parent = parent
        self.server_core = server_core
        self.original_username = username
        self.on_saved = on_saved
        self.account = self.server_core.get_account(username)

        if not self.account:
            messagebox.showwarning("账户不存在", "此账户不存在或已被删除。", parent=parent)
            return

        self.window = tk.Toplevel(parent)
        self.window.title(f"账户设置 - {username}")
        self.window.geometry("470x520")
        self.window.resizable(False, False)
        self.window.transient(parent)

        self._build_ui()
        self._sync_restriction_controls()

    def _build_ui(self):
        frame = tk.Frame(self.window)
        frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=16)

        tk.Label(frame, text="UUID:").pack(anchor="w")
        uuid_entry = tk.Entry(frame, width=58)
        uuid_entry.insert(0, self.account["uuid"])
        uuid_entry.config(state="readonly")
        uuid_entry.pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame, text="创建时间:").pack(anchor="w")
        created_entry = tk.Entry(frame, width=58)
        created_entry.insert(0, self.account["created_at"])
        created_entry.config(state="readonly")
        created_entry.pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame, text="用户名:").pack(anchor="w")
        self.username_entry = tk.Entry(frame, width=58)
        self.username_entry.insert(0, self.account["username"])
        self.username_entry.pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame, text="密码哈希:").pack(anchor="w")
        hash_text = tk.Text(frame, height=2, wrap=tk.WORD)
        hash_text.insert("1.0", self.account.get("password_hash", ""))
        hash_text.config(state="disabled")
        hash_text.pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame, text="新密码:").pack(anchor="w")
        self.password_entry = tk.Entry(frame, width=58, show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame, text="账户状态:").pack(anchor="w")
        self.status_var = tk.StringVar(value=self.account["status"])
        status_combo = ttk.Combobox(
            frame,
            textvariable=self.status_var,
            values=("正常", "限制", "禁用"),
            state="readonly",
        )
        status_combo.pack(fill=tk.X, pady=(0, 12))
        status_combo.bind("<<ComboboxSelected>>", lambda event: self._sync_restriction_controls())

        restriction_frame = tk.LabelFrame(frame, text="限制策略")
        restriction_frame.pack(fill=tk.X, pady=(0, 16))

        restrictions = self.account.get("restrictions", {})
        self.can_send_var = tk.BooleanVar(value=restrictions.get("can_send_messages", True))
        self.can_receive_var = tk.BooleanVar(value=restrictions.get("can_receive_messages", True))

        self.can_send_check = tk.Checkbutton(
            restriction_frame,
            text="允许发言",
            variable=self.can_send_var,
        )
        self.can_send_check.pack(anchor="w", padx=10, pady=(8, 2))

        self.can_receive_check = tk.Checkbutton(
            restriction_frame,
            text="允许查看消息",
            variable=self.can_receive_var,
        )
        self.can_receive_check.pack(anchor="w", padx=10, pady=(2, 8))

        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="保存", width=10, command=self._save).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="取消", width=10, command=self.window.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _sync_restriction_controls(self):
        state = tk.NORMAL if self.status_var.get() == "限制" else tk.DISABLED
        self.can_send_check.config(state=state)
        self.can_receive_check.config(state=state)

    def _save(self):
        restrictions = {
            "can_send_messages": self.can_send_var.get(),
            "can_receive_messages": self.can_receive_var.get(),
        }

        try:
            account = self.server_core.update_account(
                self.original_username,
                self.username_entry.get(),
                self.password_entry.get(),
                self.status_var.get(),
                restrictions,
            )
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.window)
            return

        if not account:
            messagebox.showwarning("保存失败", "账户不存在。", parent=self.window)
            return

        if self.on_saved:
            self.on_saved()
        self.window.destroy()
