#!/usr/bin/env python3

import os
import sys

from gi.repository import Gtk

from src.builder import Builder
from ui.main_window import MainWindow

def main():
    ui_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    ui_path = os.path.join(ui_path, 'ui/replication_monitor.glade')
    builder = Builder(ui_path)
    win = MainWindow(builder)
    Gtk.main()

if __name__ == '__main__':
    main()
