#!/usr/bin/env python3

import os
import sys

try:
    import gi
except Exception as ex:
    print('Unable to load the GTK+ gi module.\n'
          'Is GTK+ installed on your operating system and the gi module installed into Python?\n'
          'The error reported is: ' + str(ex))
    sys.exit(1)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# if we are running as a module make sure relative imports still work
if __name__ != '__main__':
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from src.builder import Builder
from ui.main_window import MainWindow


def main():
    glade_path = os.path.dirname(os.path.realpath(__file__))
    glade_path = os.path.join(glade_path, 'ui/replication_monitor.glade')
    builder = Builder(glade_path)
    win = MainWindow(builder)
    Gtk.main()

if __name__ == '__main__':
    main()
