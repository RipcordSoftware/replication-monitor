from src.gtk_helper import GtkHelper


class InfobarWarningsViewModel:
    def __init__(self, infobar, message):
        self._infobar = infobar
        self._message = message

    @property
    @GtkHelper.invoke_func_sync
    def message(self):
        return self._message.get_text()

    @message.setter
    @GtkHelper.invoke_func
    def message(self, value):
        if isinstance(value, Exception):
            self._message.set_text('{}: {}'.format(type(value).__name__, str(value)))
        else:
            self._message.set_text(str(value))
        self.show(True)

    @GtkHelper.invoke_func
    def show(self, show):
        self._infobar.show() if show else self._infobar.hide()
