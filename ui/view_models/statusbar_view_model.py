import threading

from src.gtk_helper import GtkHelper


class StatusBarViewModel:
    def __init__(self, statusbar, busy_spinner):
        self._statusbar = statusbar
        self._busy_spinner = busy_spinner

    @GtkHelper.invoke_func
    def reset(self):
        self._statusbar.remove_all(0)
        self._statusbar.push(0, 'Not Connected')

    def update(self, model):
        def func():
            try:
                signature = model.signature
                server = model.database_type.name + ' ' + str(signature.version)

                auth_details = 'Admin Party'
                session = model.session
                user_ctx = session.userCtx
                if user_ctx and user_ctx.name:
                    auth_details = user_ctx.name
                    roles = ''
                    for role in user_ctx.roles:
                        roles += ', ' + role if len(roles) > 0 else role
                    auth_details += ' [' + roles + ']'

                status = server + ' - ' + auth_details

                GtkHelper.invoke(lambda: self._statusbar.push(0, status))
            except:
                self.reset()
        thread = threading.Thread(target=func)
        thread.run()

    @GtkHelper.invoke_func
    def show_busy_spinner(self, show):
        self._busy_spinner.set_visible(show)
