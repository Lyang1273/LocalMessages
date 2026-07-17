import urwid


class LoginView:
    def __init__(self, app):
        self.app = app
        self.server_edit = urwid.Edit("服务器: ", "127.0.0.1")
        self.port_edit = urwid.Edit("端口: ", "5000")
        self.name_edit = urwid.Edit("用户名: ")
        self.info_text = urwid.Text("")

        connect_button = urwid.Button("连接")
        urwid.connect_signal(connect_button, "click", self.on_connect)

        server_button = urwid.Button("创建服务器")
        urwid.connect_signal(server_button, "click", self.on_create_server)

        pile = urwid.Pile([
            self.server_edit,
            self.port_edit,
            self.name_edit,
            urwid.Divider(),
            connect_button,
            server_button,
            urwid.Divider(),
            self.info_text,
        ])

        self.widget = urwid.Filler(
            urwid.LineBox(pile, title="连接服务器"),
            valign="top",
        )

    def on_connect(self, button):
        username = self.name_edit.edit_text.strip()
        if not username:
            self.info_text.set_text("请输入用户名")
            return
        self.app.show_chat(username)

    def on_create_server(self, button):
        self.app.show_server()


class ChatView:
    def __init__(self, app, username):
        self.app = app
        self.username = username

        self.messages = urwid.SimpleFocusListWalker([])
        self.message_list = urwid.ListBox(self.messages)
        self.input_edit = urwid.Edit("> ")

        send_button = urwid.Button("发送")
        urwid.connect_signal(send_button, "click", self.on_send)

        back_button = urwid.Button("断开")
        urwid.connect_signal(back_button, "click", self.on_back)

        footer = urwid.Columns([
            ("weight", 1, self.input_edit),
            ("pack", send_button),
            ("pack", back_button),
        ], dividechars=1)

        self.widget = urwid.Frame(
            header=urwid.Text(f"聊天中 - {username}"),
            body=urwid.LineBox(self.message_list, title="消息"),
            footer=urwid.LineBox(footer, title="输入"),
        )

    def on_send(self, button):
        text = self.input_edit.edit_text.strip()
        if not text:
            return
        self.messages.append(urwid.Text(f"{self.username}: {text}"))
        self.input_edit.edit_text = ""
        self.message_list.set_focus(len(self.messages) - 1)

    def on_back(self, button):
        self.app.show_login()


class ServerView:
    def __init__(self, app):
        self.app = app

        self.logs = urwid.SimpleFocusListWalker([
            urwid.Text("服务器已启动")
        ])
        self.log_list = urwid.ListBox(self.logs)
        self.users = urwid.SimpleFocusListWalker([
            urwid.Text("user1"),
            urwid.Text("user2"),
        ])
        self.user_list = urwid.ListBox(self.users)

        back_button = urwid.Button("停止服务器")
        urwid.connect_signal(back_button, "click", self.on_back)

        body = urwid.Columns([
            ("weight", 2, urwid.LineBox(self.log_list, title="日志")),
            ("weight", 1, urwid.LineBox(self.user_list, title="在线用户")),
        ], dividechars=1)

        self.widget = urwid.Frame(
            header=urwid.Text("服务器管理"),
            body=body,
            footer=back_button,
        )

    def on_back(self, button):
        self.app.show_login()


class App:
    def __init__(self):
        self.loop = urwid.MainLoop(
            urwid.SolidFill(" "),
            unhandled_input=self.unhandled_input,
        )
        self.current_view = None
        self.show_login()

    def show_login(self):
        self.current_view = LoginView(self)
        self.loop.widget = self.current_view.widget

    def show_chat(self, username):
        self.current_view = ChatView(self, username)
        self.loop.widget = self.current_view.widget

    def show_server(self):
        self.current_view = ServerView(self)
        self.loop.widget = self.current_view.widget

    def unhandled_input(self, key):
        if key in ("q", "Q"):
            raise urwid.ExitMainLoop()
        if key == "esc":
            self.show_login()

    def run(self):
        self.loop.run()


if __name__ == "__main__":
    App().run()