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
import time 
import sys 
import os 
import shutil
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gtk, Gdk, GObject
import logging

import common.Config as Config
from   common.Util.CSoundClient import new_csound_client
from   common.Util.Profiler import TP

from   Jam.JamMain import JamMain
from   common.Util.Trackpad import Trackpad
from   gettext import gettext as _
import subprocess
from sugar3.activity import activity

if Config.HAVE_TOOLBOX:
    from sugar3.graphics.toolbarbox import ToolbarBox
    from sugar3.activity import widgets


class TamTamJam(activity.Activity):
    def __init__(self, handle):
        # !!!!!! initialize threading in gtk !!!!!
        # ! this is important for the networking !
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        Gdk.threads_init()

        activity.Activity.__init__(self, handle)

        for snd in ['mic1', 'mic2', 'mic3', 'mic4']:
            if not os.path.isfile(os.path.join(Config.DATA_DIR, snd)):
                shutil.copyfile(Config.SOUNDS_DIR + '/' + snd, Config.DATA_DIR + '/' + snd)
                os.system('chmod 0777 ' + Config.DATA_DIR + '/' + snd + ' &')

        color = Gdk.color_parse(Config.WS_BCK_COLOR)
        self.modify_bg(Gtk.StateType.NORMAL, color)

        self.set_title('TamTam Jam')
        self.set_resizable(False)

        self.trackpad = Trackpad(self)

        self.preloadTimeout = None

        self.connect('notify::active', self.onActive)
        self.connect('destroy', self.onDestroy)

        toolbox = ToolbarBox()
        toolbox.toolbar.insert(widgets.ActivityToolbarButton(self), -1)
        toolbox.toolbar.insert(Gtk.SeparatorToolItem(), -1)

        self.trackpad.setContext('jam')

        self.set_toolbar_box(toolbox)

        self.jam = JamMain(self)
        self.connect('key-press-event', self.jam.onKeyPress)
        self.connect('key-release-event', self.jam.onKeyRelease)
        #self.modeList[mode].regenerate()
        self.jam.onActivate(arg=None)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbox.toolbar.insert(separator, -1)
        toolbox.toolbar.insert(widgets.StopButton(self), -1)

        toolbox.toolbar.show_all()
        self.set_canvas(self.jam)

        self.show_all()

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
            logging.debug('Jam.onActivate disconnecting csound')
            csnd = new_csound_client()
            csnd.connect(False)
        else:
            logging.debug('Jam.onActivate connecting csound')
            csnd = new_csound_client()
            csnd.connect(True)

    def onKeyPress(self, widget, event):
        pass

    def onKeyRelease(self, widget, event):
        pass

    def onDestroy(self, arg2):
        if Config.DEBUG: 
                print('DEBUG: TamTam::onDestroy()')

        self.jam.onDestroy()

        csnd = new_csound_client()
        csnd.connect(False)
        csnd.destroy()

        Gtk.main_quit()

    def ensure_dir(self, dir, perms=0o777, rw=os.R_OK | os.W_OK):
        if not os.path.isdir(dir):
            try:
                os.makedirs(dir, perms)
            except OSError as e:
                print('ERROR: failed to make dir %s: %i (%s)\n' % (dir, e.errno, e.strerror))
        if not os.access(dir, rw):
            print('ERROR: directory %s is missing required r/w access\n' % dir)

    def read_file(self, file_path):
        self.jam.handleJournalLoad(file_path)

    def write_file(self, file_path):
        self.jam.handleJournalSave(file_path)
