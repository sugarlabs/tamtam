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

from gi.repository import Gtk, GObject


import time

import common.Config as Config
from   common.Util.CSoundClient import new_csound_client
from   common.Util.Profiler import TP

#from   common.Util.InstrumentPanel import InstrumentPanel
from   Edit.MainWindow import MainWindow
from   common.Util.Trackpad import Trackpad
from   gettext import gettext as _
import subprocess
from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity import widgets

class TamTamEdit(activity.Activity):
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)

#        for snd in ['mic1','mic2','mic3','mic4','lab1','lab2','lab3','lab4', 'lab5', 'lab6']:
#            if not os.path.isfile(os.path.join(Config.DATA_DIR, snd)):
#                shutil.copyfile(Config.SOUNDS_DIR + '/' + snd , Config.DATA_DIR + '/' + snd)
#                os.system('chmod 0777 ' + Config.DATA_DIR + '/' + snd + ' &')

        #color = gtk.gdk.color_parse(Config.WS_BCK_COLOR)
        #self.modify_bg(gtk.STATE_NORMAL, color)

        self.set_resizable(False)

        self.trackpad = Trackpad(self)

        self.preloadTimeout = None

        self.connect('notify::active', self.onActive)
        self.connect('destroy', self.onDestroy)

        #load the sugar toolbar
        if Config.HAVE_TOOLBOX:
            # no sharing
            self.max_participants = 1

            self.toolbox = ToolbarBox()
            self.toolbox.toolbar.insert(widgets.ActivityToolbarButton(self), -1)
        else:
            self.toolbox = activity.ActivityToolbox(self)
            self.set_toolbox(self.toolbox)

            self.activity_toolbar = self.toolbox.get_activity_toolbar()

        self.toolbox.show()

        self.trackpad.setContext('edit')
        self.edit = MainWindow(self)
        self.connect('key-press-event', self.edit.onKeyPress)
        self.connect('key-release-event', self.edit.onKeyRelease)
        #self.modeList[mode].regenerate()

        self.set_canvas(self.edit)

        self.edit.onActivate(arg=None)

        if Config.HAVE_TOOLBOX:
            separator = Gtk.SeparatorToolItem()
            separator.props.draw = False
            separator.set_expand(True)
            self.toolbox.toolbar.insert(separator, -1)
            self.toolbox.toolbar.insert(widgets.StopButton(self), -1)
            self.toolbox.toolbar.show_all()
            self.set_toolbar_box(self.toolbox)
        else:
            self.activity_toolbar.share.hide()

        self.show()

    def onPreloadTimeout(self):
        if Config.DEBUG > 4: 
                print("TamTam::onPreloadTimeout", self.preloadList)

        t = time.time()
        if self.preloadList[0].load(t + 0.100):  # finished preloading this object
            self.preloadList.pop(0)
            if not len(self.preloadList):
                if Config.DEBUG > 1: 
                        print("TamTam::finished preloading", time.time() - t)
                self.preloadTimeout = False
                return False  # finished preloading everything

        if Config.DEBUG > 4: 
                print("TamTam::preload returned after", time.time() - t)

        return True

    def onActive(self, widget=None, event=None):
        if widget.props.active == False:
            csnd = new_csound_client()
            csnd.connect(False)
        else:
            csnd = new_csound_client()
            csnd.connect(True)

    def onKeyPress(self, widget, event):
        pass

    def onKeyRelease(self, widget, event):
        pass

    def onDestroy(self, arg2):
        if Config.DEBUG: 
                print('DEBUG: TamTam::onDestroy()')

        self.edit.onDestroy()

        csnd = new_csound_client()
        csnd.connect(False)
        csnd.destroy()

        Gtk.main_quit()

# No more dir created by TamTam
    def ensure_dir(self, dir, perms=0o777, rw=os.R_OK | os.W_OK):
        if not os.path.isdir(dir):
            try:
                os.makedirs(dir, perms)
            except OSError as e:
                print('ERROR: failed to make dir %s: %i (%s)\n' % (dir, e.errno, e.strerror))
        if not os.access(dir, rw):
            print('ERROR: directory %s is missing required r/w access\n' % dir)

    def read_file(self, file_path):
        self.edit.handleJournalLoad(file_path)

    def write_file(self, file_path):
        self.edit.handleJournalSave(file_path)
