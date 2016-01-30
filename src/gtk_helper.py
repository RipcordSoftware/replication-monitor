import threading
from gi.repository import Gtk, GObject


class GtkHelper:
    """
    A class which makes living with GTK and multiple threads slightly easier
    """

    @staticmethod
    def is_gtk_thread():
        """
        Determines if the current thread is the main GTK thread
        :return: True if the current thread is the main GTK thread, False otherwise
        """
        return threading.current_thread().name is 'MainThread'

    @staticmethod
    def invoke(func, async=True):
        """
        Invokes a callable func on the main GTK thread
        :param func: The callable to invoke
        :param async: When True the callable will execute asynchronously
        :return: if executed on the main thread or synchronously then the returns the result of func, otherwise None
        """
        result = None

        if GtkHelper.is_gtk_thread():
            result = func()
        else:
            event = threading.Event() if async is not True else None

            def task():
                nonlocal func, result

                result = func()
                if event is not None:
                    event.set()

            GObject.idle_add(task)

            if event is not None:
                event.wait()

        return result

    @staticmethod
    def idle(task):
        """
        Adds a task to the Gtk queue for processing
        :param task: the task (function/lambda) to run
        :return: nothing
        """
        GObject.idle_add(task)

    @staticmethod
    def invoke_func(func):
        """
        A decorator for functions which should be run on the main Gtk thread. The function is
        executed asynchronously
        :param func: The callable to run on the UI thread
        :return: nothing
        """
        def inner(*args, **kwargs):
            GtkHelper.invoke(lambda: func(*args, **kwargs))
        return inner

    @staticmethod
    def invoke_func_sync(func):
        """
        A decorator for functions which should be run on the main Gtk thread. If run from a non-UI
        thread the caller will block until the function completes
        :param func: The callable to run on the UI thread
        :return: The value returned by the callable
        """
        def inner(*args, **kwargs):
            return GtkHelper.invoke(lambda: func(*args, **kwargs), False)
        return inner

    @staticmethod
    def run_dialog(win, message_type, buttons_type, msg):
        dialog = Gtk.MessageDialog(win, 0, message_type, buttons_type, msg)
        response = dialog.run()
        dialog.destroy()
        return response
