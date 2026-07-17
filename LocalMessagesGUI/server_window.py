import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext


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

        tk.Button(
            ctrl_frame,
            text="停止服务器",
            command=self.close,
        ).pack(side=tk.LEFT, padx=5)

        main_pane = tk.Frame(self.root)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = tk.Frame(main_pane)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="服务器日志").pack(anchor=tk.W)

        self.server_log_text = scrolledtext.ScrolledText(
            left_frame,
            state=tk.DISABLED,
        )
        self.server_log_text.pack(fill=tk.BOTH, expand=True)
        self.server_log_text.tag_config("time", foreground="#999999")
        self.server_log_text.tag_config("info", foreground="#000000")
        self.server_log_text.tag_config("success", foreground="#2e7d32")
        self.server_log_text.tag_config("error", foreground="#c62828")

        right_frame = tk.Frame(main_pane, width=250)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="在线用户").pack(anchor=tk.W)

        self.user_listbox = tk.Listbox(
            right_frame,
            selectmode=tk.SINGLE,
            exportselection=False,
        )
        self.user_listbox.pack(fill=tk.BOTH, expand=True)

        user_action_frame = tk.Frame(right_frame)
        user_action_frame.pack(fill=tk.X, pady=(8, 0))

        self.force_disconnect_button = tk.Button(
            user_action_frame,
            text="强制下线",
            command=self._force_disconnect_selected_user,
            state=tk.DISABLED,
        )
        self.force_disconnect_button.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(0, 4),
        )

        self.mute_button = tk.Button(
            user_action_frame,
            text="禁言",
            command=self._mute_selected_user,
            state=tk.DISABLED,
        )
        self.mute_button.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(4, 0),
        )

        self.user_listbox.bind(
            "<<ListboxSelect>>",
            self._on_user_selected,
        )

    def server_log(self, message):
        if self.root.winfo_exists():
            self.root.after(0, self._server_log_impl, message)

    def _server_log_impl(self, message):
        if not self.root.winfo_exists():
            return

        self.server_log_text.config(state=tk.NORMAL)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.server_log_text.insert(tk.END, f"[{timestamp}] ", "time")

        if message.startswith("[+]") or message.startswith("Server listening"):
            tag = "success"
        elif message.startswith("[-]") or "error" in message.lower():
            tag = "error"
        else:
            tag = "info"

        self.server_log_text.insert(tk.END, f"{message}\n", tag)
        self.server_log_text.see(tk.END)
        self.server_log_text.config(state=tk.DISABLED)

    def update_user_list(self, users):
        if self.root.winfo_exists():
            self.root.after(0, self._update_user_list_impl, users)

    def _update_user_list_impl(self, users):
        if not self.root.winfo_exists():
            return

        self.user_listbox.delete(0, tk.END)

        for user in users:
            self.user_listbox.insert(tk.END, user)

        self.force_disconnect_button.config(state=tk.DISABLED)
        self.mute_button.config(state=tk.DISABLED, text="禁言")

    def _get_selected_username(self):
        selection = self.user_listbox.curselection()

        if not selection:
            return None

        display_name = self.user_listbox.get(selection[0])

        if display_name.startswith("[Mute] "):
            return display_name[len("[Mute] "):]

        return display_name

    def _on_user_selected(self, event):
        username = self._get_selected_username()

        if not username:
            self.force_disconnect_button.config(state=tk.DISABLED)
            self.mute_button.config(state=tk.DISABLED, text="禁言")
            return

        is_muted = self.server_core.is_user_muted(username)

        self.force_disconnect_button.config(state=tk.NORMAL)
        self.mute_button.config(
            state=tk.NORMAL,
            text="解除禁言" if is_muted else "禁言",
        )

    def _force_disconnect_selected_user(self):
        username = self._get_selected_username()

        if not username:
            return

        self._confirm_force_disconnect(username)

    def _confirm_force_disconnect(self, username):
        first_confirmed = messagebox.askyesno(
            "确认强制下线",
            f"确定要强制下线用户“{username}”吗？",
            parent=self.root,
        )

        if not first_confirmed:
            return

        second_confirmed = messagebox.askyesno(
            "再次确认",
            f"此操作将立即断开“{username}”的连接，是否继续？",
            parent=self.root,
        )

        if not second_confirmed:
            return

        if not self.server_core.force_disconnect(username):
            messagebox.showwarning(
                "操作失败",
                f"用户“{username}”已离线。",
                parent=self.root,
            )

    def _mute_selected_user(self):
        username = self._get_selected_username()

        if not username:
            return

        if self.server_core.is_user_muted(username):
            confirmed = messagebox.askyesno(
                "解除禁言",
                f"确定要解除用户“{username}”的禁言吗？",
                parent=self.root,
            )

            if not confirmed:
                return

            if not self.server_core.unmute_user(username):
                messagebox.showwarning(
                    "操作失败",
                    f"用户“{username}”已离线。",
                    parent=self.root,
                )
            return

        confirmed = messagebox.askyesno(
            "确认禁言",
            f"确定要禁言用户“{username}”吗？",
            parent=self.root,
        )

        if not confirmed:
            return

        if not self.server_core.mute_user(username):
            messagebox.showwarning(
                "操作失败",
                f"用户“{username}”已离线。",
                parent=self.root,
            )

    def close(self):
        if self.server_core:
            self.server_core.stop()

        if self.on_close:
            self.on_close()
