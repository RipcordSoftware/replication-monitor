class AboutDialog:
    def __init__(self, builder):
        self._win = builder.get_object('dialog_about', target=self, include_children=True)

    def run(self):
        result = self._win.run()
        self._win.hide()
        return result