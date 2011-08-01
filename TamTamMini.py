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
locale.setlocale(locale.LC_NUMERIC, 'C')
import signal 
import time 
import sys 
import os 
import shutil
import pygtk

pygtk.require('2.0')

import gtk

import gobject
import time

import common.Util.Instruments
import common.Config as Config
from   common.Util.CSoundClient import new_csound_client
from   common.Util.Profiler import TP

from   Mini.miniTamTamMain import miniTamTamMain
from   common.Util.Trackpad import Trackpad
from   gettext import gettext as _
import commands
from sugar.activity import activity
try:
    from sugar.graphics.toolbarbox import ToolbarBox
    HAVE_TOOLBOX = True
except ImportError:
    HAVE_TOOLBOX = False

if HAVE_TOOLBOX:
    from sugar.activity.widgets import ActivityToolbarButton
    from sugar.activity.widgets import StopButton


class TamTamMini(activity.Activity):

    __gtype_name__ = 'TamTamMiniWindow'

    def __init__(self, handle):
        self.mini = None

        activity.Activity.__init__(self, handle)

        color = gtk.gdk.color_parse(Config.WS_BCK_COLOR)
        self.modify_bg(gtk.STATE_NORMAL, color)

        self.set_title('TamTam Mini')
        self.set_resizable(False)

        self.trackpad = Trackpad(self)
        self.trackpad.setContext('mini')

        self.connect('notify::active', self.onActive)
        self.connect('destroy', self.onDestroy)

        #load the sugar toolbar
        self.have_toolbox = HAVE_TOOLBOX
        if self.have_toolbox:
            self.toolbox = ToolbarBox()
            activity_button = ActivityToolbarButton(self)
            self.toolbox.toolbar.insert(activity_button, 0)
            activity_button.show()
        else:
            self.toolbox = activity.ActivityToolbox(self)
            self.set_toolbox(self.toolbox)

        self.toolbox.show()

        self.mini = miniTamTamMain(self)
        self.mini.onActivate(arg=None)
        self.mini.updateInstrumentPanel()
        #self.modeList[mode].regenerate()

        self.set_canvas(self.mini)
        self.show()

    def do_size_allocate(self, allocation):
        activity.Activity.do_size_allocate(self, allocation)
        if self.mini is not None:
            self.mini.updateInstrumentPanel()

    def onActive(self, widget=None, event=None):
        if widget.props.active == False:
            csnd = new_csound_client()
            csnd.connect(False)
        else:
            csnd = new_csound_client()
            csnd.connect(True)

    def onDestroy(self, arg2):
        if Config.DEBUG: 
                print 'DEBUG: TamTam::onDestroy()'

        self.mini.onDestroy()

        csnd = new_csound_client()
        csnd.connect(False)
        csnd.destroy()

        gtk.main_quit()

# no more dir created by TamTam
    def ensure_dir(self, dir, perms=0777, rw=os.R_OK | os.W_OK):
        if not os.path.isdir(dir):
            try:
                os.makedirs(dir, perms)
            except OSError, e:
                print 'ERROR:Failed to make dir %s: %i (%s)\n' % (dir, e.errno, e.strerror)
        if not os.access(dir, rw):
            print 'ERROR: directory %s is missing required r/w access\n' % dir

    def read_file(self, file_path):
        self.metadata['tamtam_subactivity'] = 'mini'

    def write_file(self, file_path):
        f = open(file_path, 'w')
        f.close()

    def add_stop_button(self):
        ''' Add a stop button if using the new toolbars '''
        if self.have_toolbox:
            separator = gtk.SeparatorToolItem()
            separator.props.draw = False
            separator.set_expand(True)
            self.toolbox.toolbar.insert(separator, -1)
            separator.show()
            stop_button = StopButton(self)
            stop_button.props.accelerator = '<Ctrl>q'
            self.toolbox.toolbar.insert(stop_button, -1)
            stop_button.show()
