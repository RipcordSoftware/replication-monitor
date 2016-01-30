from src.gtk_helper import GtkHelper


class InfobarWarningsViewModel:
    def __init__(self, infobar, message):
        self._infobar = infobar
        self._message = message

    @property
    def message(self):
        value = None

        def func():
            nonlocal value
            value = self._message.get_text()
        GtkHelper.invoke(func, False)
        return value

    @message.setter
    def message(self, value):
        def func():
            self._message.set_text(value)
            self.show(True)
        GtkHelper.invoke(func)

    def show(self, show):
        if show:
            GtkHelper.invoke(self._infobar.show)
        else:
            GtkHelper.invoke(self._infobar.hide)
