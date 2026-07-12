import tkinter
import tkinter.messagebox as messagebox


class ConnectWindow:
    def __init__(self, parent, on_success=None):
        self.parent = parent
        self.on_success = on_success
        self.window = tkinter.Toplevel(parent)
        self.window.title("Local Messages - 连接服务器")
        self.window.geometry("300x200")

        self.window.protocol("WM_DELETE_WINDOW", self.quitLocalMessages)

        self.ip_entry = None
        self.port_entry = None
        self.createWidgets()

    def createWidgets(self):
        ip_label = tkinter.Label(self.window, text="IP地址")
        ip_label.pack(side="top", pady=(20, 0))

        self.ip_entry = tkinter.Entry(self.window)
        self.ip_entry.pack(side="top", pady=2)

        port_label = tkinter.Label(self.window, text="端口号")
        port_label.pack(side="top", pady=2)

        self.port_entry = tkinter.Entry(self.window)
        self.port_entry.pack(side="top", pady=2)

        create_server_button = tkinter.Button(self.window, text="创建服务器", relief="flat", fg="blue", font=("宋体", 9))
        create_server_button.pack(side="bottom", pady=(5, 5))

        connect_button = tkinter.Button(self.window, text="连接", width=8, command=self.on_connect)
        connect_button.pack(side="bottom")

    def on_connect(self):
        ip = self.ip_entry.get().strip()
        port_text = self.port_entry.get().strip()

        if not ip:
            messagebox.showerror("输入错误", "请输入有效的 IP 地址。")
            return

        if not self._is_valid_ip(ip):
            messagebox.showerror("输入错误", "IP 地址格式不正确。")
            return

        if not port_text:
            messagebox.showerror("输入错误", "端口号不能为空。")
            return

        try:
            port = int(port_text)
        except ValueError:
            messagebox.showerror("输入错误", "端口号格式错误。")
            return

        if port < 1 or port > 65535:
            messagebox.showerror("输入错误", "端口号错误。")
            return

        # 直接调用，传递 ip 和 port 给回调
        self.connectionSuccess(ip, port)

    def _is_valid_ip(self, ip):
        parts = ip.split('.')
        if len(parts) != 4:
            return False

        for part in parts:
            if not part.isdigit():
                return False
            value = int(part)
            if value < 0 or value > 255:
                return False

        return True

    def connectionSuccess(self, ip=None, port=None):
        self.window.destroy()
        if self.on_success:
            try:
                # 尝试按新签名调用回调
                if ip is not None and port is not None:
                    self.on_success(ip, port)
                else:
                    self.on_success()
            except TypeError:
                # 回调不接受参数时的回退
                self.on_success()

    def quitLocalMessages(self):
        import sys
        self.parent.destroy()
        sys.exit(0)
