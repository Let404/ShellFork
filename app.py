import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from ui.main_window import MainWindow


class ShellForkApplication(Gtk.Application):

    def __init__(self):
        super().__init__(application_id="io.github.shellfork")

    def do_activate(self):

        window = MainWindow(self)

        window.present()