from gi.repository import Gtk
import xml.etree.ElementTree as ET

class Builder:
    _builder = Gtk.Builder()

    def __init__(self, filename):
        with open(filename, 'rt') as f:
            ui = f.read()

        self.ui_root = ET.fromstring(ui)
        self._builder.add_from_string(ui)

    def get_object(self, ui_id, target=None):
        win = self._builder.get_object(ui_id)

        if win and target:
            path = ".//object[@id='" + ui_id + "']"
            ui_root_object = self.ui_root.find(path)
            ui_objects = ui_root_object.findall('.//object/signal/..')
            ui_objects.append(ui_root_object)

            for ui_object in ui_objects:

                ui_child_id = ui_object.attrib['id']
                child_win = self._builder.get_object(ui_child_id)
                ui_signals = ui_object.findall('./signal')

                for ui_signal in ui_signals:
                    event_name = ui_signal.attrib['name']
                    handler_name = ui_signal.attrib['handler']
                    handler = getattr(target, handler_name)
                    child_win.connect(event_name, handler)

        return win

    def get_children(self, ui_id, target):
        path = ".//object[@id='" + ui_id + "']//object"
        ui_objects = self.ui_root.findall(path)

        for ui_object in ui_objects:
            child_id = ui_object.attrib['id']
            child_win = self._builder.get_object(child_id)
            setattr(target, child_id, child_win)

    def connect_signals(self, obj):
        self._builder.connect_signals(obj)