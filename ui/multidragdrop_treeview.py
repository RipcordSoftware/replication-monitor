# Derived from Kevin Mehall's excellent article at: https://kevinmehall.net/2010/pygtk_multi_select_drag_drop
# License added in his stead:
#
# The MIT License (MIT)
# Copyright (c) 2010 Kevin Mehall
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from gi.repository import Gdk


class MultiDragDropTreeView:
    # TreeView that captures mouse events to make drag and drop work properly

    def __init__(self):
        self._control = None

    def attach(self, control):
        self._control = control

        self._control.connect('button_press_event', self.on_button_press)
        self._control.connect('button_release_event', self.on_button_release)
        self._control.defer_select = False

    def on_button_press(self, widget, event):
        # Here we intercept mouse clicks on selected items so that we can
        # drag multiple items without the click selecting only one
        target = self._control.get_path_at_pos(int(event.x), int(event.y))
        if (target
            and event.type == Gdk.EventType.BUTTON_PRESS
            and not (event.state & (Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.SHIFT_MASK))
            and self._control.get_selection().path_is_selected(target[0])):
                # disable selection
                self._control.get_selection().set_select_function(lambda *ignore: False)
                self._control.defer_select = target[0]

    def on_button_release(self, widget, event):
        # re-enable selection
        self._control.get_selection().set_select_function(lambda *ignore: True)

        target = self._control.get_path_at_pos(int(event.x), int(event.y))
        if (self._control.defer_select and target
            and self._control.defer_select == target[0]
            and not (event.x==0 and event.y==0)):  # certain drag and drop
                self._control.set_cursor(target[0], target[1], False)

        self._control.defer_select=False
