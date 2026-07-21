import tkinter as tk
from tkinter import ttk, messagebox


class ServerConfigWindow:
    def __init__(self, parent, on_confirm=None, on_cancel=None):
        self.parent = parent
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        # 默认配置
        self.config = {
            "host": "0.0.0.0",
            "port": 5000,
            "max_users": 100,
            "max_message_length": 10000,
            "max_username_length": 20,
            "heartbeat_timeout": 25,
            "enable_logging": True,
            "server_name": "LocalMessages",
        }

        self.window = tk.Toplevel(parent)
        self.window.title("服务器配置")
        self.window.geometry("365x400")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build_ui()

    def _build_ui(self):
        # 标题
        title_label = tk.Label(self.window, text="服务器配置")
        title_label.pack(pady=(15, 0))

        # 主框架
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # 服务器名称
        row1 = tk.Frame(main_frame)
        row1.pack(fill='x', padx=10, pady=5)
        tk.Label(row1, text="服务器名称:", anchor='w').pack(side='left')
        self.server_name_entry = tk.Entry(row1, width=20)
        self.server_name_entry.insert(0, self.config["server_name"])
        self.server_name_entry.pack(side='right', padx=5)

        # IP地址
        row2 = tk.Frame(main_frame)
        row2.pack(fill='x', padx=10, pady=5)
        tk.Label(row2, text="监听地址:", anchor='w').pack(side='left')
        self.host_entry = tk.Entry(row2, width=20)
        self.host_entry.insert(0, self.config["host"])
        self.host_entry.pack(side='right', padx=5)

        # 端口
        row3 = tk.Frame(main_frame)
        row3.pack(fill='x', padx=10, pady=5)
        tk.Label(row3, text="端口号:", anchor='w').pack(side='left')
        self.port_entry = tk.Entry(row3, width=20)
        self.port_entry.insert(0, str(self.config["port"]))
        self.port_entry.pack(side='right', padx=5)

        # 最多同时在线人数
        row4 = tk.Frame(main_frame)
        row4.pack(fill='x', padx=10, pady=5)
        tk.Label(row4, text="最多同时在线人数:", anchor='w').pack(side='left')
        self.max_users_entry = tk.Entry(row4, width=20)
        self.max_users_entry.insert(0, str(self.config["max_users"]))
        self.max_users_entry.pack(side='right', padx=5)

        # 用户名最大长度
        row5 = tk.Frame(main_frame)
        row5.pack(fill='x', padx=10, pady=5)
        tk.Label(row5, text="用户名最大长度:", anchor='w').pack(side='left')
        self.max_username_entry = tk.Entry(row5, width=20)
        self.max_username_entry.insert(0, str(self.config["max_username_length"]))
        self.max_username_entry.pack(side='right', padx=5)

        # 消息最大长度
        row6 = tk.Frame(main_frame)
        row6.pack(fill='x', padx=10, pady=5)
        tk.Label(row6, text="消息最大长度（字符）:", anchor='w').pack(side='left')
        self.max_message_entry = tk.Entry(row6, width=20)
        self.max_message_entry.insert(0, str(self.config["max_message_length"]))
        self.max_message_entry.pack(side='right', padx=5)

        # 超时时间
        row7 = tk.Frame(main_frame)
        row7.pack(fill='x', padx=10, pady=5)
        tk.Label(row7, text="超时时间（秒）:", anchor='w').pack(side='left')
        self.heartbeat_entry = tk.Entry(row7, width=20)
        self.heartbeat_entry.insert(0, str(self.config["heartbeat_timeout"]))
        self.heartbeat_entry.pack(side='right', padx=5)

        # 记录日志
        row8 = tk.Frame(main_frame)
        row8.pack(fill='x', padx=10, pady=5)
        self.logging_var = tk.BooleanVar(value=self.config["enable_logging"])
        tk.Checkbutton(row8, text="记录日志", variable=self.logging_var, anchor='w').pack(side='left')

        button_frame = tk.Frame(self.window)
        button_frame.pack(fill='x', padx=20, pady=15)

        ttk.Separator(self.window, orient='horizontal').pack(fill='x', padx=20)

        # 取消按钮
        cancel_btn = tk.Button(button_frame, text="取消", command=self._on_cancel, width=7)
        cancel_btn.pack(side='right', padx=5)

        # 启动按钮
        start_btn = tk.Button(button_frame, text="启动服务器", command=self._on_confirm, width=12)
        start_btn.pack(side='right', padx=5)

    def _on_confirm(self):
        """确认配置并启动"""
        try:
            # 获取并验证配置
            config = {
                "server_name": self.server_name_entry.get().strip(),
                "host": self.host_entry.get().strip(),
                "port": int(self.port_entry.get().strip()),
                "max_users": int(self.max_users_entry.get().strip()),
                "max_username_length": int(self.max_username_entry.get().strip()),
                "max_message_length": int(self.max_message_entry.get().strip()),
                "heartbeat_timeout": int(self.heartbeat_entry.get().strip()),
                "enable_logging": self.logging_var.get(),
            }

            # 验证
            if not config["server_name"]:
                messagebox.showerror("配置错误", "服务器名称不能为空")
                return

            if not config["host"]:
                messagebox.showerror("配置错误", "监听地址不能为空")
                return

            if not 1 <= config["port"] <= 65535:
                messagebox.showerror("配置错误", "端口号必须在 1~65535 之间")
                return

            if config["max_users"] < 1:
                messagebox.showerror("配置错误", "最多同时在线人数必须大于 0")
                return

            if config["max_username_length"] < 1:
                messagebox.showerror("配置错误", "用户名最大长度必须大于 0")
                return

            if config["max_message_length"] < 1:
                messagebox.showerror("配置错误", "消息最大长度必须大于 0")
                return

            if config["heartbeat_timeout"] < 1:
                messagebox.showerror("配置错误", "超时时间必须大于 0")
                return

            self.config = config
            self.window.destroy()

            if self.on_confirm:
                self.on_confirm(config)

        except ValueError:
            messagebox.showerror("配置错误", "请输入有效的数字")

    def _on_cancel(self):
        """取消配置"""
        self.window.destroy()
        if self.on_cancel:
            self.on_cancel()

    def get_config(self):
        """获取配置"""
        return self.config
