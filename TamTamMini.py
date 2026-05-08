#Copyright (c) 2007-8 Jean Piche, Olivier Belanger, James Bergstra
#Copyright (c) 2007-8 Nathanael Lecaude, Adrian Martin, Eric Lamothe
#Copyright (c) 2009-11 Aleksey Lim, Chris Leonard, Douglas Eck
#Copyright (c) 2009-11 Gonzalo Odiard, James Cameron, Jorge Saldivar
#Copyright (c) 2009-11 Marco Pesenti Gritti, Rafael Ortiz, Sean Wood
#Copyright (c) 2011 Walter Bender

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import locale
import os
import logging
import gi

# Set locale for number formatting
locale.setlocale(locale.LC_NUMERIC, 'C')

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gtk, Gdk, GObject

import common.Config as Config
from   common.Util.CSoundClient import new_csound_client

from   Mini.miniTamTamMain import miniTamTamMain
from   common.Util.Trackpad import Trackpad
from   gettext import gettext as _
from sugar3.activity import activity

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity import widgets
from sugar3.activity.widgets import DescriptionItem


class TamTamMini(activity.Activity):

    __gtype_name__ = 'TamTamMiniWindow'

    def __init__(self, handle):
        self.mini = None

        activity.Activity.__init__(self, handle)

        # Set background color using CSS for GTK3+
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(f"""
            .tamtam-window {{
                background-color: {Config.WS_BCK_COLOR};
            }}
        """.encode())
        
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.set_title('TamTam Mini')
        self.set_resizable(False)

        self.trackpad = Trackpad(self)
        self.trackpad.setContext('mini')

        self.connect('notify::active', self.onActive)
        self.connect('destroy', self.onDestroy)

        #load the sugar toolbar
        toolbox = ToolbarBox()
        toolbox.toolbar.insert(widgets.ActivityButton(self), -1)
        toolbox.toolbar.insert(widgets.TitleEntry(self), -1)

        description_item = DescriptionItem(self)
        toolbox.toolbar.insert(description_item, -1)
        description_item.show()

        toolbox.toolbar.insert(widgets.ShareButton(self), -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbox.toolbar.insert(separator, -1)

        toolbox.toolbar.insert(widgets.StopButton(self), -1)
        toolbox.toolbar.show_all()

        toolbox.show()
        self.set_toolbar_box(toolbox)

        self.mini = miniTamTamMain(self)
        self.mini.onActivate(arg=None)
        self.mini.updateInstrumentPanel()

        #self.modeList[mode].regenerate()

        # Add the main widget to the activity
        canvas = Gtk.Overlay()
        canvas.add(self.mini)
        
        # Set up the activity canvas
        self.set_canvas(canvas)
        
        # Set size based on screen size
        screen = Gdk.Screen.get_default()
        width = screen.get_width()
        height = screen.get_height()
        self.set_size_request(width, height)
        
        # Show all widgets and set focus
        self.show_all()
        self.mini.instrumentPanel.grab_focus()
        
        logging.info('Activity startup completed')

    def do_size_allocate(self, allocation):
        activity.Activity.do_size_allocate(self, allocation)
        if self.mini is not None:
            logging.error('TamTamMini size alloc %s', (allocation.x, allocation.y, allocation.width, allocation.height))
            self.mini.updateInstrumentPanel()

    def onActive(self, widget, param):
        if self.mini is not None:
            self.mini.onActivate(param)

    def onDestroy(self, widget, event=None):
        if self.mini is not None:
            self.mini.onDestroy()

        csnd = new_csound_client()
        csnd.connect(False)
        csnd.destroy()

        Gtk.main_quit()

    def ensure_dir(self, dir, perms=0o777, rw=os.R_OK | os.W_OK):
        if not os.path.isdir(dir):
            try:
                os.makedirs(dir, perms)
            except OSError as e:
                print(f'ERROR: Failed to make dir {dir}: {e.errno} ({e.strerror})')
        if not os.access(dir, rw):
            print(f'ERROR: directory {dir} is missing required r/w access')

    def read_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except (IOError, OSError) as error:
            logging.error(f'Error reading file {file_path}: {str(error)}')
            return None

    def write_file(self, file_path, data):
        try:
            with open(file_path, 'w') as f:
                f.write(data)
            return True
        except (IOError, OSError) as error:
            logging.error(f'Error writing file {file_path}: {str(error)}')
            return False
    def write_file(self, file_path):
        f = open(file_path, 'w')
        f.close()
