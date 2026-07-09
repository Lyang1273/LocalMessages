import threading
import tkinter as tk
from tkinter import messagebox, Frame, Label, Button, Entry
from LocalMessagesCore.client import NetworkClient
from LocalMessagesCore.server.server_core import ChatServerCore
from LocalMessagesGUI.chat_window import ChatWindow
from LocalMessagesGUI.server_window import ServerWindow


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Local Messages - 登录")
        self.root.geometry("380x270")
        self.root.resizable(False, False)

        self.network = None
        self.server_core = None
        self.server_thread = None
        self.username = ""
        self.chat_window = None
        self.server_window = None
        self._connecting = False
        self._starting_server = False

        self._setup_login()
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _setup_login(self):
        self.login_frame = Frame(self.root)
        self.login_frame.pack(expand=True, pady=(10, 10))

        Label(self.login_frame, text="服务器:").pack(anchor="w")
        self.server_entry = Entry(self.login_frame, width=30)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.pack(pady=(0, 10))

        Label(self.login_frame, text="端口:").pack(anchor="w")
        self.port_entry = Entry(self.login_frame, width=30)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(pady=(0, 10))

        Label(self.login_frame, text="用户名:").pack(anchor="w")
        self.name_entry = Entry(self.login_frame, width=30)
        self.name_entry.pack(pady=(0, 15))

        self.connect_button = Button(
            self.login_frame,
            text="连接",
            command=self._do_connect,
            width=15,
        )
        self.connect_button.pack()

        self.server_link_label = Label(
            self.login_frame,
            text="创建服务器",
            fg="blue",
            cursor="hand2",
        )
        self.server_link_label.pack(pady=(20, 0))
        self.server_link_label.bind("<Button-1>", lambda e: self._create_server_window())

    def _do_connect(self):
        if self._connecting:
            return

        host = self.server_entry.get().strip()
        port_text = self.port_entry.get().strip()
        username = self.name_entry.get().strip()

        if not host:
            messagebox.showwarning("输入错误", "请输入服务器地址。")
            return

        if not username:
            messagebox.showwarning("输入错误", "请输入用户名。")
            return

        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showwarning("输入错误", "端口必须是 1 到 65535 之间的整数。")
            return

        self._connecting = True
        self.connect_button.config(state=tk.DISABLED)
        self.username = username

        threading.Thread(
            target=self._connect_worker,
            args=(host, port, username),
            daemon=True,
        ).start()

    def _connect_worker(self, host, port, username):
        try:
            network = NetworkClient(
                on_message=self._handle_network_message,
                on_close=self._handle_network_close,
            )
            network.connect(host, port, username)

            self.root.after(0, lambda: self._on_connect_success(network, username))
        except Exception as exc:
            self.root.after(0, lambda: self._on_connect_failed(str(exc)))

    def _on_connect_success(self, network, username):
        self.network = network
        self._connecting = False
        self.connect_button.config(state=tk.NORMAL)

        self.root.withdraw()

        chat_toplevel = tk.Toplevel(self.root)
        self.chat_window = ChatWindow(
            chat_toplevel,
            self.network,
            username,
            on_close=self._on_chat_closed,
        )

    def _handle_network_message(self, msg):
        if self.chat_window is not None:
            try:
                if self.chat_window.root.winfo_exists():
                    self.chat_window.root.after(0, lambda: self.chat_window.handle_message(msg))
            except Exception:
                pass

    def _handle_network_close(self):
        self.root.after(0, self._on_chat_closed)

    def _on_connect_failed(self, error_message):
        self._connecting = False
        self.connect_button.config(state=tk.NORMAL)
        messagebox.showerror("连接失败", f"无法连接到服务器。\n\n{error_message}")

    def _on_connect_failed(self, error_message):
        self._connecting = False
        self.connect_button.config(state=tk.NORMAL)
        messagebox.showerror("连接失败", f"无法连接到服务器。\n\n{error_message}")

    def _on_chat_closed(self):
        if self.network:
            try:
                disconnect_method = getattr(self.network, "disconnect", None)
                if callable(disconnect_method):
                    disconnect_method()
            except Exception:
                pass
            finally:
                self.network = None

        if self.chat_window is not None:
            try:
                if self.chat_window.root.winfo_exists():
                    self.chat_window.root.destroy()
            except Exception:
                pass
            finally:
                self.chat_window = None

        self.root.deiconify()

    def _create_server_window(self):
        if self._starting_server:
            return

        if self.server_window is not None:
            try:
                if self.server_window.root.winfo_exists():
                    self.server_window.root.deiconify()
                    self.server_window.root.lift()
                    self.server_window.root.focus_force()
                    return
            except Exception:
                self.server_window = None

        port_text = self.port_entry.get().strip()
        try:
            port = int(port_text)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showwarning("输入错误", "端口必须是 1 到 65535 之间的整数。")
            return

        self._starting_server = True
        self.server_link_label.config(state=tk.DISABLED)

        try:
            self.server_core = ChatServerCore(host="0.0.0.0", port=port)
            server_toplevel = tk.Toplevel(self.root)
            self.server_window = ServerWindow(
                server_toplevel,
                self.server_core,
                on_close=self._close_server,
            )
            self.root.withdraw()

            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
            )
            self.server_thread.start()
        except Exception as exc:
            self._starting_server = False
            self.server_link_label.config(state=tk.NORMAL)
            self.server_core = None
            if self.server_window is not None:
                try:
                    self.server_window.root.destroy()
                except Exception:
                    pass
                self.server_window = None
            messagebox.showerror("服务器启动失败", str(exc))

    def _run_server(self):
        try:
            self.server_core.start()
        except Exception as exc:
            self.root.after(0, lambda: self._on_server_start_failed(str(exc)))
        finally:
            self.root.after(0, self._on_server_stopped)

    def _on_server_start_failed(self, error_message):
        messagebox.showerror("服务器启动失败", error_message)

    def _on_server_stopped(self):
        self._starting_server = False
        self.server_link_label.config(state=tk.NORMAL)

        if self.server_window is not None:
            try:
                if self.server_window.root.winfo_exists():
                    self.server_window.root.destroy()
            except Exception:
                pass
            finally:
                self.server_window = None

        self.server_core = None
        self.server_thread = None
        self.root.deiconify()

    def _close_server(self):
        if self.server_core:
            try:
                stop_method = getattr(self.server_core, "stop", None)
                if callable(stop_method):
                    stop_method()
            except Exception:
                pass

    def _quit(self):
        if self.server_core:
            try:
                stop_method = getattr(self.server_core, "stop", None)
                if callable(stop_method):
                    stop_method()
            except Exception:
                pass

        if self.network:
            try:
                disconnect_method = getattr(self.network, "disconnect", None)
                if callable(disconnect_method):
                    disconnect_method()
            except Exception:
                pass

        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
