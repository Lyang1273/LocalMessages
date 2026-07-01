import tkinter
import sys


def start():
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