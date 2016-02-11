from gi.repository import Gtk
import xml.etree.ElementTree as ET
import codecs


class Builder:
    """
    A class which behaves a bit like the GTK builder - but is more useful.
    It will load a glade file and create member variables for child objects
    and wire events to member functions.
    """
    _builder = Gtk.Builder()

    def __init__(self, filename):
        """
        Construct a builder object based on a glade file
        :param filename: The path to the glade file
        :return: Nothing
        """
        self._builder.add_from_file(filename)

        with codecs.open(filename, 'r', 'utf-8') as f:
            ui = f.read()
        self.ui_root = ET.fromstring(ui)

    def get_object(self, ui_id, target=None, include_children=False):
        """
        Finds the object in the glade DOM and optionally wires up signals and creates member fields for
        GTK+ child objects.
        :param ui_id: The id of the object in the glade DOM
        :param target: The target python object to wire GTK+ events to
        :param include_children: When True an instance variable will be added to target for each child GTK+ object
        :return: The GTK+ window instance
        """
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

            if include_children:
                self._get_children(ui_id, target)

        return win

    def _get_children(self, ui_id, target):
        path = ".//object[@id='" + ui_id + "']//object"
        ui_objects = self.ui_root.findall(path)

        for ui_object in ui_objects:
            child_id = ui_object.attrib['id']
            child_win = self._builder.get_object(child_id)
            setattr(target, child_id, child_win)

