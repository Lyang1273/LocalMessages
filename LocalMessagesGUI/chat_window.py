import tkinter
import sys


class ChatWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Local Messages")
        self.root.geometry("800x500")

        self.root.protocol("WM_DELETE_WINDOW", self.quitLocalMessages)

        self.createWidgets()


    def createWidgets(self):
        menubar = tkinter.Menu(self.root)
        self.root.config(menu=menubar)
        menubar.add_command(label="退出", command=lambda: sys.exit(0))

        send_button = tkinter.Button(text="发送", height=1, width=10)
        send_button.pack(side="bottom", anchor="ne", padx=(0, 10), pady=(0, 10))

        messages_text = tkinter.Text(self.root)
        messages_text.configure(state="disabled")
        messages_text.pack(fill="both", side="top", expand=True)

        input_text = tkinter.Text(self.root, height=8)
        input_text.pack(fill="both", pady=(0, 10), side="bottom")


    def quitLocalMessages(self):
        import sys
        self.root.destroy()
        sys.exit(0)