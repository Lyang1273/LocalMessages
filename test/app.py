"""
Local Messages - 统一聊天程序
登录窗口（主窗口）与聊天/管理窗口完全分离
"""
import tkinter as tk
from tkinter import messagebox, scrolledtext, Menu, Listbox, Frame, Label, Button, Entry, Toplevel
from datetime import datetime
from client.network import NetworkClient
from server.server_core import ChatServerCore
import threading


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Local Messages - 登录")
        self.root.geometry("380x270")
        self.root.resizable(False, False)

        self.network = None
        self.server_core = None
        self.username = ""
        self.chat_window = None
        self.server_window = None

        self._setup_login()

        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    # ---------- 登录界面 ----------
    def _setup_login(self):
        self.login_frame = Frame(self.root)
        self.login_frame.pack(expand=True, pady=(10, 10))

        Label(self.login_frame, text="服务器:").pack(anchor='w')
        self.server_entry = Entry(self.login_frame, width=30)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(pady=(0, 10))

        Label(self.login_frame, text="端口:").pack(anchor='w')
        self.port_entry = Entry(self.login_frame, width=30)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(pady=(0, 10))

        Label(self.login_frame, text="用户名:").pack(anchor='w')
        self.name_entry = Entry(self.login_frame, width=30)
        self.name_entry.pack(pady=(0, 15))

        Button(self.login_frame, text="连接", command=self._do_connect, width=15).pack()

        # 纯蓝色文字链接，无额外效果
        link_label = Label(self.login_frame, text="创建服务器", fg="blue", cursor="hand2")
        link_label.pack(pady=(20, 0))
        link_label.bind("<Button-1>", lambda e: self._create_server_window())

    # ---------- 连接服务器 ----------
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
            on_message=self._client_on_message,
            on_close=self._client_on_close
        )
        try:
            self.network.connect(host, port, username)
            self.username = username
            self.root.withdraw()          # 隐藏登录窗口
            self._open_chat_window()      # 打开独立的聊天窗口
        except Exception as e:
            messagebox.showerror("连接失败", str(e))
            self.network = None

    # ---------- 创建服务器（独立窗口） ----------
    def _create_server_window(self):
        win = Toplevel(self.root)
        win.title("创建服务器")
        win.geometry("350x180")
        win.resizable(False, False)

        frame = Frame(win)
        frame.pack(expand=True, padx=20, pady=20)

        Label(frame, text="启动本地服务器", font=("Arial", 12, "bold")).pack(pady=5)

        port_frame = Frame(frame)
        port_frame.pack(pady=10)
        Label(port_frame, text="端口:").pack(side=tk.LEFT)
        port_var = tk.StringVar(value="5000")
        Entry(port_frame, textvariable=port_var, width=8).pack(side=tk.LEFT, padx=5)

        status_label = Label(frame, text="", fg="green")
        status_label.pack()

        def start_server():
            try:
                port = int(port_var.get().strip())
            except ValueError:
                messagebox.showerror("错误", "端口必须是数字")
                return

            # 检查是否已有运行中的服务器
            if self.server_core and self.server_core.running:
                messagebox.showinfo("提示", "服务器已在运行")
                win.destroy()
                return

            self.server_core = ChatServerCore(host='0.0.0.0', port=port)
            self.server_core.set_callbacks(
                on_log=lambda msg: None,   # 管理窗口会接管日志
                on_user_list_update=lambda users: None
            )
            threading.Thread(target=self.server_core.start, daemon=True).start()

            status_label.config(text="启动成功", fg="green")
            win.after(500, win.destroy)   # 关闭配置窗口
            # 隐藏登录窗口，打开管理窗口
            self.root.withdraw()
            self._open_server_window()

        def stop_server():
            if self.server_core:
                self.server_core.stop()
                self.server_core = None
            status_label.config(text="已停止", fg="red")
            start_btn.config(state=tk.NORMAL)
            stop_btn.config(state=tk.DISABLED)

        btn_frame = Frame(frame)
        btn_frame.pack(pady=10)
        start_btn = Button(btn_frame, text="启动", command=start_server, width=8)
        start_btn.pack(side=tk.LEFT, padx=5)
        stop_btn = Button(btn_frame, text="停止", command=stop_server, state=tk.DISABLED, width=8)
        stop_btn.pack(side=tk.LEFT, padx=5)

        win.protocol("WM_DELETE_WINDOW", win.destroy)

    # ---------- 独立聊天窗口 ----------
    def _open_chat_window(self):
        self.chat_window = Toplevel(self.root)
        self.chat_window.title("Local Messages - 聊天")
        self.chat_window.geometry("800x500")
        self.chat_window.protocol("WM_DELETE_WINDOW", self._close_chat)

        menubar = Menu(self.chat_window)
        self.chat_window.config(menu=menubar)
        menubar.add_command(label="断开", command=self._close_chat)
        menubar.add_command(label="退出", command=self._quit)

        # 消息显示区
        self.msg_display = scrolledtext.ScrolledText(self.chat_window)
        self.msg_display.configure(state="disabled")
        self.msg_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        self.msg_display.tag_config("own", foreground="#2196F3")
        self.msg_display.tag_config("other", foreground="#4CAF50")
        self.msg_display.tag_config("system", foreground="#FF9800")
        self.msg_display.tag_config("time", foreground="#999999")

        bottom_frame = Frame(self.chat_window)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))

        self.input_text = tk.Text(bottom_frame, height=8)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_text.bind("<Control-Return>", lambda e: self._send_message())

        send_btn = Button(bottom_frame, text="发送", command=self._send_message)
        send_btn.pack(side=tk.RIGHT, padx=(10, 0))

        self.input_text.focus_set()

    def _send_message(self):
        msg = self.input_text.get("1.0", tk.END).strip()
        if not msg or not self.network:
            return
        if self.network.send(msg):
            self.input_text.delete("1.0", tk.END)

    def _client_on_message(self, msg):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.after(0, lambda: self._handle_client_msg(msg))

    def _client_on_close(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.after(0, self._close_chat)

    def _handle_client_msg(self, msg):
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

    def _close_chat(self):
        if self.network:
            self.network.disconnect()
            self.network = None
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.destroy()
            self.chat_window = None
        self.root.deiconify()   # 显示登录窗口

    # ---------- 独立服务器管理窗口 ----------
    def _open_server_window(self):
        self.server_window = Toplevel(self.root)
        self.server_window.title("Local Messages - 服务器管理")
        self.server_window.geometry("800x500")
        self.server_window.protocol("WM_DELETE_WINDOW", self._close_server)

        menubar = Menu(self.server_window)
        self.server_window.config(menu=menubar)
        menubar.add_command(label="停止", command=self._close_server)
        menubar.add_command(label="退出", command=self._quit)

        # 控制栏
        ctrl_frame = Frame(self.server_window)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = Label(ctrl_frame, text="服务器运行中", fg="green")
        self.status_label.pack(side=tk.LEFT, padx=5)

        Button(ctrl_frame, text="停止服务器", command=self._close_server).pack(side=tk.LEFT, padx=5)

        # 主面板：日志 + 在线用户
        main_pane = Frame(self.server_window)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = Frame(main_pane)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        Label(left_frame, text="服务器日志", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.server_log = scrolledtext.ScrolledText(left_frame, state=tk.DISABLED)
        self.server_log.pack(fill=tk.BOTH, expand=True)
        self.server_log.tag_config("time", foreground="#999999")
        self.server_log.tag_config("info", foreground="#000000")
        self.server_log.tag_config("success", foreground="#4CAF50")
        self.server_log.tag_config("error", foreground="#f44336")

        right_frame = Frame(main_pane, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        Label(right_frame, text="在线用户", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.user_listbox = Listbox(right_frame)
        self.user_listbox.pack(fill=tk.BOTH, expand=True)

        # 设置回调，更新界面
        if self.server_core:
            self.server_core.set_callbacks(
                on_log=self._server_log,
                on_user_list_update=self._update_user_list
            )

    def _server_log(self, msg):
        if self.server_window and self.server_window.winfo_exists():
            self.server_window.after(0, lambda: self._server_log_impl(msg))

    def _server_log_impl(self, msg):
        self.server_log.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.server_log.insert(tk.END, f"[{timestamp}] ", "time")
        if msg.startswith("[+]") or msg.startswith("✓"):
            tag = "success"
        elif msg.startswith("[-]") or msg.startswith("✗"):
            tag = "error"
        else:
            tag = "info"
        self.server_log.insert(tk.END, msg + "\n", tag)
        self.server_log.see(tk.END)
        self.server_log.config(state=tk.DISABLED)

    def _update_user_list(self, users):
        if self.server_window and self.server_window.winfo_exists():
            self.server_window.after(0, lambda: self._update_user_list_impl(users))

    def _update_user_list_impl(self, users):
        self.user_listbox.delete(0, tk.END)
        for u in users:
            self.user_listbox.insert(tk.END, u)

    def _close_server(self):
        if self.server_core:
            self.server_core.stop()
            self.server_core = None
        if self.server_window and self.server_window.winfo_exists():
            self.server_window.destroy()
            self.server_window = None
        self.root.deiconify()   # 显示登录窗口

    # ---------- 退出 ----------
    def _quit(self):
        if self.server_core:
            self.server_core.stop()
        if self.network:
            self.network.disconnect()
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = App()
    app.run()