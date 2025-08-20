from gi.repository import Gtk

import time

import common.Config as Config
from common.Util.ThemeWidgets import *
from common.Util import InstrumentDB
from common.port.scrolledbox import HScrolledBox
import sugar3.graphics.style as style

import logging


INSTRUMENT_SIZE = Config.scale(114)

Tooltips = Config.Tooltips


class InstrumentPanel( Gtk.EventBox ):
    def __init__(self,setInstrument=None):
        Gtk.EventBox.__init__(self)

        self._scrolled_window = None

        self.instrumentDB = InstrumentDB.getRef()
        self.setInstrument = setInstrument
        self.playInstrument = None
        self.micRec = None
        self.synthRec = None
        self.rowLen = None
        self.enterMode = False

        self.instDic = None

        self.loaded = False
        self.loadData = {}

    def grab_focus(self):
        if not self.instDic:
            return
        for button in list(self.instDic.values()):
            if button.props.active:
                button.grab_focus()
                break

    def configure( self, setInstrument = None, playInstrument = None, enterMode = False, micRec = None, synthRec = None, rowLen = 8, width = -1 ):

        self.setInstrument = setInstrument
        self.playInstrument = playInstrument
        self.enterMode = enterMode
        self.micRec = micRec

        if width != -1:
            rowLen = width / INSTRUMENT_SIZE
        if self.rowLen == rowLen:
            return

        self.rowLen = rowLen

        if self.loaded:
            self.prepareInstrumentTable(self.category)

    def load(self):
        if self.loaded:
            return True

        color = Gdk.color_parse(Config.PANEL_BCK_COLOR)
        self.modify_bg(Gtk.StateType.NORMAL, color)
        self.instTable = None
        self.recstate = False

        self.mainVBox =  Gtk.VBox()

        self.loadInstrumentList()
        self.loadToolbar()

        if self.instDic == None:
            self.instDic = {}

        self.loadInstDic(self.instDic)

        self.loadInstrumentViewport()

        self.prepareInstrumentTable()

        self.add(self.mainVBox)
        self.show_all()

        self.loaded = True
        return True

    def loadInstrumentList(self):

        self.instrumentList = { "all": [], "all.enterMode": [], "percussions.enterMode": [], "mysounds": [] }
        for category in Config.CATEGORIES:
            self.instrumentList[category] = []

        keys = list(self.instrumentDB.instNamed.keys())
        for i in range(len(keys)):
            key = keys[i]

            instrument = self.instrumentDB.instNamed[key]
            if not instrument.kitStage and not instrument.kit:
                if not key.startswith('mic') and not key.startswith('lab'):
                    self.instrumentList["all"].append( key )
                    self.instrumentList["all.enterMode"].append( key )
                self.instrumentList[instrument.category].append( key )
                if instrument.category == "percussions":
                    self.instrumentList["percussions.enterMode"].append( key )

        self.instrumentList["mysounds"].sort()

        self.instrumentList["all"] += self.instrumentList["mysounds"]
        self.instrumentList["all.enterMode"] += self.instrumentList["mysounds"]

    def loadToolbar(self):
        self.toolbarBox = Gtk.HBox()

        scrollbox = HScrolledBox(scroll_policy=Gtk.PolicyType.NEVER)
        scrollbox.set_viewport(self.toolbarBox)
        scrollbox.modify_bg(Gtk.StateType.NORMAL,
                style.Color(Config.PANEL_BCK_COLOR).get_gdk_color())
        self.mainVBox.pack_start(scrollbox, False, False, 0)

        self.firstTbBtn = None

        for i in range(len(Config.CATEGORIES)):
            category = Config.CATEGORIES[i]

            btn = ImageRadioButton(self.firstTbBtn,
                    category + '.png', category + 'sel.png',
                    category + 'sel.png')

            if self.firstTbBtn == None:
                self.firstTbBtn = btn
            btn.connect('clicked',self.handleToolbarBtnPress,category)
            btn.set_tooltip_text(str(category))
            self.toolbarBox.pack_start(btn, False, False, 0)

    def loadInstDic( self, instDic):

        self.firstInstButton = None

        for instrument in self.instrumentList['all']:
            try:
                btn = ImageRadioButton(
                        self.firstInstButton, instrument + '.png',
                        instrument + 'sel.png', instrument + 'sel.png')
            except:
                btn = ImageRadioButton(
                        self.firstInstButton, 'generic.png',
                        'genericsel.png', 'genericsel.png')

            btn.clickedHandler = btn.connect('clicked',self.handleInstrumentButtonClick, instrument)
            btn.connect('enter',self.handleInstrumentButtonEnter, instrument)
            btn.connect('focus-in-event', self.handleInstrumentButtonFocus, instrument)

            btn.set_tooltip_text(str(self.instrumentDB.instNamed[instrument].nameTooltip))
            instDic[instrument] = btn
            if self.firstInstButton == None:
                self.firstInstButton = btn

    def loadInstrumentViewport( self ):
        self.instBox = Gtk.Alignment.new(0.5, 0, 0, 1)

        box = Gtk.EventBox()
        color = Gdk.color_parse(Config.INSTRUMENT_GRID_COLOR)
        box.modify_bg(Gtk.StateType.NORMAL, color)
        box.add(self.instBox)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrollwin.add_with_viewport(box)

        box.get_parent().set_shadow_type(Gtk.ShadowType.NONE)
        self.mainVBox.pack_end(scrollwin, True, True, 0)

        self.show_all()

    def prepareInstrumentTable(self,category = 'all'):
        self.category = category

        if self.enterMode:
            if category == "all": category = "all.enterMode"
            elif category == "percussions": category = "percussions.enterMode"

        if self.instTable != None:
            for child in self.instTable.get_children():
                self.instTable.remove(child)
            self.instBox.remove(self.instTable)
            self.instTable.destroy()

        instrumentNum = len(self.instrumentList[category])
        instruments = self.instrumentList[category]

        cols = self.rowLen
        if instrumentNum < cols:
            cols = instrumentNum
        rows = (instrumentNum // cols)
        if instrumentNum % cols is not 0:    #S'il y a un reste
            rows = rows + 1

        self.instTable = Gtk.Table(rows,cols,True)
        self.instTable.set_row_spacings(0)
        self.instTable.set_col_spacings(0)

        for row in range(rows):
            for col in range(cols):
                i = row*cols+col
                if i >= instrumentNum:
                    break
                inst = instruments[i]
                if inst in self.instDic:
                    self.instTable.attach(self.instDic[inst], col, col + 1,
                            row, row + 1, Gtk.AttachOptions.SHRINK,
                            Gtk.AttachOptions.SHRINK, 0, 0)
        self.instBox.add(self.instTable)
        self.instTable.show_all()

    def selectFirstCat(self):
        self.firstTbBtn.set_active(True)

    def handleToolbarBtnPress(self, widget, category):
        if widget.get_active():
            self.prepareInstrumentTable(category)

    def handleInstrumentButtonClick(self,widget,instrument):
        if widget.get_active() is True and self.recstate == False:
            if self.setInstrument:
                #widget.event( Gdk.Event( Gdk.LEAVE_NOTIFY )  ) # fake the leave event
                self.setInstrument(instrument)
            time.sleep(0.05)
            if self.playInstrument: self.playInstrument(instrument)
            if self.enterMode:
                pass #Close the window

    def handleInstrumentButtonEnter(self,widget,instrument):
        if self.enterMode and self.playInstrument:
            self.playInstrument(instrument)

    def handleInstrumentButtonFocus(self, widget, event, instrument):
        if self._scrolled_window is None:
            parent = widget.get_parent()
            while parent is not None:
                if isinstance(parent, Gtk.ScrolledWindow):
                    self._scrolled_window = parent
                    break
                parent = parent.get_parent()
            else:
                return
        top = self._scrolled_window

        __, shift = widget.translate_coordinates(top, 0, 0)
        if shift < 0:
            top.props.vadjustment.props.value += shift
        else:
            shift += widget.get_allocation().height + Config.PANEL_SPACING
            top_height = top.get_allocation().height
            if shift > top_height:
                top.props.vadjustment.props.value += (shift - top_height)

    def handleMicRecButtonClick(self,widget,mic):
        self.recstate = False
        self.setInstrument(mic)
        if self.micRec: self.micRec(mic)

    def handleRecButtonPress(self,widget,btn):
        self.recstate = True
        btn.set_active(True)

    def set_activeInstrument(self,instrument, state):
        if len(self.instDic) > 0:
            for key in self.instDic:
                if key == instrument:
                    btn = self.instDic[key].get_children()[0]
                    btn.handler_block(btn.clickedHandler)
                    btn.set_active(state)
                    btn.handler_unblock(btn.clickedHandler)


class DrumPanel( Gtk.EventBox ):
    def __init__(self, setDrum = None):
        Gtk.EventBox.__init__(self)
        color = Gdk.color_parse(Config.PANEL_BCK_COLOR)
        self.modify_bg(Gtk.StateType.NORMAL, color)

        self.setDrum = setDrum
        self.instrumentList = []
        keys = list(self.instrumentDB.instNamed.keys())
        for key in keys:
            if self.instrumentDB.instNamed[key].category == "kit":
                self.instrumentList.append( key )
        self.instrumentList.sort()
        self.drawDrums()

    def drawDrums(self):
        firstBtn = None
        btnBox = RoundHBox(fillcolor = '#6F947B', bordercolor = Config.PANEL_BCK_COLOR, radius = Config.PANEL_RADIUS)
        btnBox.set_border_width(Config.PANEL_SPACING)
        self.drums = {}
        for drumkit in self.instrumentList:
            instBox = Gtk.VBox()
            self.drums[drumkit] = ImageRadioButton(firstBtn, drumkit + '.png',
                    drumkit + 'sel.png', drumkit + 'sel.png')
            self.drums[drumkit].clickedHandler = self.drums[drumkit].connect('clicked',self.setDrums,drumkit)
            if firstBtn == None:
                firstBtn = self.drums[drumkit]
            instBox.pack_start(self.drums[drumkit], False, False, 0)
            btnBox.pack_start(instBox, False, False, 0)
        self.add(btnBox)
        self.show_all()

    def setDrums(self,widget,data):
        if widget.get_active():
            if self.setDrum:
                widget.event( Gdk.Event( Gdk.LEAVE_NOTIFY )  ) # fake the leave event
                self.setDrum(data)

    def set_activeInstrument( self, instrument, state ):
        if instrument in self.instrumentList:
            btn = self.drums[instrument]
            btn.handler_block(btn.clickedHandler)
            btn.set_active(state)
            btn.handler_unblock(btn.clickedHandler)
