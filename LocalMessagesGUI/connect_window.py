import tkinter


class ConnectWindow:
    def __init__(self, parent, on_success=None):
        self.parent = parent
        self.on_success = on_success
        self.window = tkinter.Toplevel(parent)
        self.window.title("连接至设备")
        self.window.geometry("300x200")
        
        self.window.protocol("WM_DELETE_WINDOW", self.quitLocalMessages)

        self.createWidgets()
        
        
    def createWidgets(self):
        ip_label = tkinter.Label(self.window, text="IP地址")
        ip_label.pack(side="top", pady=(20, 0))

        ip_entry = tkinter.Entry(self.window)
        ip_entry.pack(side="top", pady=2)

        port_label = tkinter.Label(self.window, text="端口号")
        port_label.pack(side="top", pady=2)

        port_entry = tkinter.Entry(self.window)
        port_entry.pack(side="top", pady=2)

        connect_button = tkinter.Button(self.window, text="连接", width=8, command=self.on_connect)
        connect_button.pack(side="bottom", pady=20)


    def on_connect(self):
        self.window.after(1000, self.connectionSuccess)


    def connectionSuccess(self):
        self.window.destroy()
        if self.on_success:
            self.on_success()
        
        
    def quitLocalMessages(self):
        import sys
        self.parent.destroy()
        sys.exit(0)