import pygtk
pygtk.require( '2.0' )
import gtk

import time

import common.Config as Config
from common.Util.ThemeWidgets import *
from common.Util import InstrumentDB
from common.port.scrolledbox import HScrolledBox
import sugar.graphics.style as style
import logging


INSTRUMENT_SIZE = Config.scale(114)

Tooltips = Config.Tooltips


class InstrumentPanel( gtk.EventBox ):
    def __init__(self,setInstrument=None):
        gtk.EventBox.__init__(self)

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
        self.loadStage = [0,0,0]

    def grab_focus(self):
        if not self.instDic:
            return
        for widget in self.instDic.values():
            button = widget.get_children()[0]
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

    def load( self, timeout = -1 ):
        if self.loaded: return True
        if Config.DEBUG > 4: print "InstrumentPanel load", self.loadStage

        if self.loadStage[0] == 0:
            color = gtk.gdk.color_parse(Config.PANEL_BCK_COLOR)
            self.modify_bg(gtk.STATE_NORMAL, color)
            self.loadStage[0] = 1
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 1:
            self.tooltips = gtk.Tooltips()
            self.loadStage[0] = 2
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 2:
            self.instTable = None
            self.recstate = False
            self.lastInstrumentWidget = None

            self.mainVBox =  gtk.VBox()
            self.loadStage[0] = 3
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 3:
            if not self.loadInstrumentList( timeout, self.loadStage ):
                return False
            self.loadStage[0] = 4
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 4:
            if not self.loadToolbar( timeout, self.loadStage ):
                return False
            self.loadStage[0] = 5
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 5:
            if self.instDic == None:
                self.instDic = {}
                self.loadStage[0] = 5.1
            else:
                self.loadStage[0] = 6

        if self.loadStage[0] == 5.1:
            if not self.loadInstDic( self.instDic, timeout, self.loadStage ):
                return False
            self.loadStage[0] = 6
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 6:
            self.loadInstrumentViewport()
            self.loadStage[0] = 7
            if timeout >= 0 and time.time() > timeout: return False

        if self.loadStage[0] == 7:
            self.prepareInstrumentTable()
            self.loadStage[0] = 8
            if timeout >= 0 and time.time() > timeout: return False

        self.add(self.mainVBox)
        self.show_all()

        self.loaded = True
        return True

    def loadInstrumentList( self, timeout = -1, loadStage = [0,0,0] ):

        if loadStage[1] == 0:
            self.instrumentList = { "all": [], "all.enterMode": [], "percussions.enterMode": [], "mysounds": [] }
            for category in Config.CATEGORIES:
                self.instrumentList[category] = []
            loadStage[1] = 1
            if timeout >= 0 and time.time() > timeout: return False

        if loadStage[1] == 1:
            keys = self.instrumentDB.instNamed.keys()
            for i in range(loadStage[2], len(keys)):
                key = keys[i]

                instrument = self.instrumentDB.instNamed[key]
                if not instrument.kitStage and not instrument.kit:
                    if not key.startswith('mic') and not key.startswith('lab'):
                        self.instrumentList["all"].append( key )
                        self.instrumentList["all.enterMode"].append( key )
                    self.instrumentList[instrument.category].append( key )
                    if instrument.category == "percussions":
                        self.instrumentList["percussions.enterMode"].append( key )
                loadStage[2] += 1
                if timeout >= 0 and time.time() > timeout: return False

            loadStage[1] = 2
            loadStage[2] = 0

        self.instrumentList["mysounds"].sort()

        self.instrumentList["all"] += self.instrumentList["mysounds"]
        self.instrumentList["all.enterMode"] += self.instrumentList["mysounds"]

        loadStage[1] = 0
        return True

    def loadToolbar( self, timeout = -1, loadStage = [0,0,0] ):
        if loadStage[1] == 0:
            self.toolbarBox = gtk.HBox()

            scrollbox = HScrolledBox(scroll_policy=gtk.POLICY_NEVER)
            scrollbox.set_viewport(self.toolbarBox)
            scrollbox.modify_bg(gtk.STATE_NORMAL, style.Color(Config.PANEL_BCK_COLOR).get_gdk_color())
            self.mainVBox.pack_start(scrollbox, False, False)

            self.firstTbBtn = None
            self.loadStage[1] = 1
            if timeout >= 0 and time.time() > timeout: return False

        for i in range(loadStage[1]-1, len(Config.CATEGORIES)):
            category = Config.CATEGORIES[i]
            if loadStage[2] == 0:
                self.loadData["btnBox"] = RoundVBox(fillcolor = Config.CATEGORY_BCK_COLOR, bordercolor = Config.PANEL_BCK_COLOR, radius = Config.PANEL_RADIUS)
                self.loadData["btnBox"].set_border_width(Config.PANEL_SPACING)
                loadStage[2] = 1
                if timeout >= 0 and time.time() > timeout: return False

            if loadStage[2] == 1:
                self.loadData["btn"] = ImageRadioButton(self.firstTbBtn,
                        category + '.png', category + 'sel.png',
                        category + 'sel.png')
                loadStage[2] = 2
                if timeout >= 0 and time.time() > timeout: return False

            if self.firstTbBtn == None:
                self.firstTbBtn = self.loadData["btn"]
            self.loadData["btn"].connect('clicked',self.handleToolbarBtnPress,category)
            self.tooltips.set_tip(self.loadData["btn"],str(category))
            self.loadData["btnBox"].add(self.loadData["btn"])
            self.toolbarBox.pack_start(self.loadData["btnBox"],True,True)

            loadStage[2] = 0
            loadStage[1] += 1
            if timeout >= 0 and time.time() > timeout: return False

        self.loadData.pop("btn")
        self.loadData.pop("btnBox")
        loadStage[1] = 0
        return True

    def loadInstDic( self, instDic, timeout = -1, loadStage = [0,0,0] ):

        if loadStage[1] == 0:
            self.firstInstButton = None
            self.loadData["len"] = len(self.instrumentList['all'])
            loadStage[1] = 1
            if timeout >= 0 and time.time() > timeout: return False


        for i in range( loadStage[1]-1, self.loadData["len"] ):
            instrument = self.instrumentList["all"][i]
            if loadStage[2] == 0:
                self.loadData["instBox"] = RoundVBox(fillcolor = Config.INST_BCK_COLOR, bordercolor = Config.INSTRUMENT_GRID_COLOR, radius = Config.PANEL_RADIUS)
                self.loadData["instBox"].set_border_width(Config.PANEL_SPACING)
                loadStage[2] = 1
                if timeout >= 0 and time.time() > timeout: return False

            if loadStage[2] == 1:
                try:
                    self.loadData['instButton'] = ImageRadioButton(
                            self.firstInstButton, instrument + '.png',
                            instrument + 'sel.png', instrument + 'sel.png')
                except:
                    self.loadData["instButton"] = ImageRadioButton(
                            self.firstInstButton, 'generic.png',
                            'genericsel.png', 'genericsel.png')
                loadStage[2] = 2
                if timeout >= 0 and time.time() > timeout: return False

            if loadStage[2] == 2:
                self.loadData["instButton"].clickedHandler = self.loadData["instButton"].connect('clicked',self.handleInstrumentButtonClick, instrument)
                self.loadData["instButton"].connect('enter',self.handleInstrumentButtonEnter, instrument)
                self.loadData["instButton"].connect('focus-in-event', self.handleInstrumentButtonFocus, instrument)
                loadStage[2] = 3
                if timeout >= 0 and time.time() > timeout: return False

            self.tooltips.set_tip(self.loadData["instBox"],str(self.instrumentDB.instNamed[instrument].nameTooltip))

            self.loadData["instBox"].pack_start(self.loadData["instButton"],False,False)
            instDic[instrument] = self.loadData["instBox"]
            if self.firstInstButton == None:
                self.firstInstButton = self.loadData["instButton"]
            loadStage[2] = 0
            if timeout >= 0 and time.time() > timeout: return False

            loadStage[1] += 1

        self.loadData.pop("instBox")
        self.loadData.pop("instButton")
        self.loadData.pop("len")
        loadStage[1] = 0
        return True

    def loadInstrumentViewport( self ):
        self.instBox = gtk.Alignment(0.5, 0, 0, 1)

        box = gtk.EventBox()
        color = gtk.gdk.color_parse(Config.INSTRUMENT_GRID_COLOR)
        box.modify_bg(gtk.STATE_NORMAL, color)
        box.add(self.instBox)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_NEVER,gtk.POLICY_AUTOMATIC)
        scrollwin.add_with_viewport(box)
        box.get_parent().set_shadow_type(gtk.SHADOW_NONE)
        self.mainVBox.pack_end(scrollwin)

        self.show_all()

    def prepareInstrumentTable(self,category = 'all'):
        self.category = category

        if self.enterMode:
            if category == "all": category = "all.enterMode"
            elif category == "percussions": category = "percussions.enterMode"

        if self.instTable != None:
            for child in self.instTable.get_children()[:]:
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

        self.instTable = gtk.Table(rows,cols,True)
        self.instTable.set_row_spacings(0)
        self.instTable.set_col_spacings(0)

        for row in range(rows):
            for col in range(cols):
                i = row*cols+col
                if i >= instrumentNum:
                    break
                inst = instruments[i]
                if self.instDic.has_key(inst):
                    self.instTable.attach(self.instDic[inst], col, col+1, row, row+1, gtk.SHRINK, gtk.SHRINK, 0, 0)

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
                widget.event( gtk.gdk.Event( gtk.gdk.LEAVE_NOTIFY )  ) # fake the leave event
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
            parent = widget.parent
            while parent is not None:
                if isinstance(parent, gtk.ScrolledWindow):
                    self._scrolled_window = parent
                    break
                parent = parent.parent
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


class DrumPanel( gtk.EventBox ):
    def __init__(self, setDrum = None):
        gtk.EventBox.__init__(self)
        color = gtk.gdk.color_parse(Config.PANEL_BCK_COLOR)
        self.modify_bg(gtk.STATE_NORMAL, color)

        self.setDrum = setDrum
        self.instrumentList = []
        keys = self.instrumentDB.instNamed.keys()
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
            instBox = RoundVBox(fillcolor = Config.INST_BCK_COLOR, bordercolor = Config.PANEL_COLOR, radius = Config.PANEL_RADIUS)
            instBox.set_border_width(Config.PANEL_SPACING)
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
                widget.event( gtk.gdk.Event( gtk.gdk.LEAVE_NOTIFY )  ) # fake the leave event
                self.setDrum(data)

    def set_activeInstrument( self, instrument, state ):
        if instrument in self.instrumentList:
            btn = self.drums[instrument]
            btn.handler_block(btn.clickedHandler)
            btn.set_active(state)
            btn.handler_unblock(btn.clickedHandler)

if __name__ == "__main__":
    win = gtk.Window()
    wc = DrumPanel(None)
    win.add(wc)
    win.show()
    #start the gtk event loop
    gtk.main()
