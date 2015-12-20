import threading
from gi.repository import GObject


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