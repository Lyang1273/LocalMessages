import tkinter
import sys
from LocalMessagesGUI.connect_window import ConnectWindow


def quitLocalMessages():
    sys.exit(0)

def main():
    root = tkinter.Tk()
    root.withdraw()

    connect = ConnectWindow(root, on_success = lambda: main_window(root))

    root.mainloop()


def main_window(root):
    from LocalMessagesGUI.chat_window import ChatWindow
    root.deiconify()
    ChatWindow(root)


def connectWindow():
    connect = tkinter.Tk()
    connect.title("Local Messages")
    connect.geometry("300x200")

    connect.protocol("WM_DELETE_WINDOW", quitLocalMessages)

    ip_label = tkinter.Label(connect, text="IP地址")
    ip_label.pack(side="top", pady=(20, 0))

    ip_entry = tkinter.Entry(connect)
    ip_entry.pack(side="top", pady=2)

    port_label = tkinter.Label(connect, text="端口号")
    port_label.pack(side="top", pady=2)

    port_entry = tkinter.Entry(connect)
    port_entry.pack(side="top", pady=2)

    connect_button = tkinter.Button(connect, text="连接", width=8, command=lambda: connect.destroy())
    connect_button.pack(side="bottom", pady=20)

    connect.mainloop()

def start():
    connectWindow()

    home = tkinter.Tk()
    home.title("Local Messages")
    home.geometry("800x500")

    menubar = tkinter.Menu(home)
    home.config(menu=menubar)
    menubar.add_command(label="退出", command=lambda: sys.exit(0))

    send_button = tkinter.Button(text="发送", height=1, width=10)
    send_button.pack(side="bottom", anchor="ne", padx=(0, 10), pady=(0, 10))

    messages_text = tkinter.Text(home)
    messages_text.configure(state="disabled")
    messages_text.pack(fill="both", side="top", expand=True)

    input_text = tkinter.Text(home, height=8)
    input_text.pack(fill="both", pady=(0, 10), side="bottom")

    home.mainloop()