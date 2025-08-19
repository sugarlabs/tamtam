from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
import cairo

import common.Util.Instruments
import common.Util.InstrumentDB as InstrumentDB
from common.Util.ThemeWidgets import RoundHBox, BigComboBox, ImageToggleButton
from common.Util.Profiler import TP
from common.Util import NoteDB
from common.Util.NoteDB import PARAMETER
from common.Util import ControlStream
from common.Util.CSoundClient import new_csound_client
from common.Util.CSoundNote import CSoundNote
from common.Config import imagefile
from EditToolbars import common_buttons
from EditToolbars import mainToolbar
from EditToolbars import recordToolbar
from EditToolbars import generateToolbar
from EditToolbars import toolsToolbar
from gettext import gettext as _
from subprocess import Popen
from sugar3.graphics.palette import Palette, Invoker
from sugar3.datastore import datastore
import time
import os
import commands
import random
from common.Util import OS
from common.port.scrolledbox import HScrolledBox
from sugar3.graphics import style
from sugar3.graphics.toolbarbox import ToolbarButton

def gdk_color_to_cairo(color):
    return (color.red/65536.0, color.green/65536.0, color.blue/65536.0)

class CONTEXT:
    PAGE = 0
    TRACK = 1
    NOTE = 2

import common.Config as Config

from common.Generation.GenerationConstants import GenerationConstants
#from Edit.Properties import Properties
from Edit.TrackInterface import TrackInterface, TrackInterfaceParasite
from Edit.TuneInterface import TuneInterface, TuneInterfaceParasite

from common.Generation.Generator import generator1, GenerationParameters


Tooltips = Config.Tooltips()
KEY_MAP_PIANO = Config.KEY_MAP_PIANO

TRACK_SIZE = Config.scale(132)
DRUM_TRACK_SIZE = Config.scale(165)


#-----------------------------------
# The main TamTam window
#-----------------------------------
class MainWindow(Gtk.EventBox):

    def __init__( self, activity ):
        Gtk.EventBox.__init__(self)
        self.instrumentDB = InstrumentDB.getRef()
        self.csnd = new_csound_client()
        #self.tooltips = Gtk.Tooltips()
        self.activity = activity

        for i in [6,7,8,9,10]:
            self.csnd.setTrackVolume(100, i)
        self.trackCount = 6

        self.scale = GenerationConstants.DEFAULT_SCALE

        # META ALGO: [section, variation or not, nPages] A B A C
        self.tuneForm = [[0, False, 2], [1, False, 4], [0, True, 2], [2, False, 2]]

        def init_data( ):
            TP.ProfileBegin("init_data")
            self._data = {}

            #[ volume, ... ]
            self._data['track_volume'] = [ Config.DEFAULT_VOLUME ] * Config.NUMBER_OF_TRACKS
            self._data['track_mute']   = [ 1.0 ] * Config.NUMBER_OF_TRACKS

            #[ instrument index, ... ]
            self.trackInstrumentDefault = [
                    self.instrumentDB.instNamed["kalimba"],
                    self.instrumentDB.instNamed["kalimba"],
                    self.instrumentDB.instNamed["kalimba"],
                    self.instrumentDB.instNamed["kalimba"],
                    self.instrumentDB.instNamed["drum2kit"] ]
            self.trackInstrument = self.trackInstrumentDefault[:]

            for i in self.trackInstrument:
                if i.kit == None:
                    self.csnd.load_instrument(i.name)
                else:
                    self.csnd.load_drumkit(i.name)

            if len(self.trackInstrument) != Config.NUMBER_OF_TRACKS: raise 'error'
            self.drumIndex = Config.NUMBER_OF_TRACKS - 1

            self.last_clicked_instTrackID = 0
            self.last_clicked_instPrimary = 'kalimba'

            #second instrument for melodic tracks
            self.trackInstrument2Default = [ None, None, None, None]
            self.trackInstrument2 = self.trackInstrument2Default[:]

            self._data['volume'] = Config.DEFAULT_VOLUME
            self._data['tempo'] = Config.PLAYER_TEMPO

            self.playScope = "Selection"
            self.displayedPage = -1
            self.trackSelected = [ 0 for i in range(Config.NUMBER_OF_TRACKS) ]
            self.trackActive = [ 1 for i in range(Config.NUMBER_OF_TRACKS) ]

            self.pages_playing = []
            self.journalCalled = False

            self.noteDB = NoteDB.NoteDB()
            TP.ProfileEnd("init_data")

        def formatRoundBox( box, fillcolor ):
            box.set_radius( 7 )
            box.set_border_width( 1 )
            box.set_fill_color( fillcolor )
            box.set_border_color( Config.PANEL_BCK_COLOR )
            return box

        def init_GUI():

            self.GUI = {}
            self.GUI["2main"] = Gtk.VBox()
            self.GUI["2instrumentPalette"] = instrumentPalette(_('Track 1 Volume'), self)

            def draw_inst_icons():
                instruments = [ k for k in self.instrumentDB.inst if not k.kitStage ]
                self.GUI["2instrumentIcons"] = {}
                for i in instruments:
                    try:
                        pixbuf = cairo.ImageSurface.create_from_png(i.img)
                    except:
                        pixbuf = cairo.ImageSurface.create_from_png(imagefile('generic.png'))
                    self.GUI['2instrumentIcons'][i.name] = pixbuf
            TP.ProfileBegin("init_GUI::instrument icons")
            draw_inst_icons()
            TP.ProfileEnd("init_GUI::instrument icons")


            #------------------------------------------------------------------------
            # page
            self.GUI["2page"] = Gtk.HBox()
            self.scrollWin = Gtk.ScrolledWindow()
            self.scrollWin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.scrollWin.add_with_viewport(self.GUI["2page"])
            self.GUI["2main"].pack_start( self.scrollWin, True , True, 0)

            if 1: # + instrument panel
                self.GUI["2instrumentPanel"] = Gtk.VBox()
                self.GUI["2page"].pack_start( self.GUI["2instrumentPanel"], True, True, 0 )
                # + + instrument 1 box
                self.GUI["2instrument1Box"] = formatRoundBox( RoundHBox(), Config.BG_COLOR )
                self.GUI["2instrument1Box"].set_size_request(-1, TRACK_SIZE)
                self.GUI["2instrument1volBox"] = Gtk.VBox()
                #self.GUI["2instrument1volumeAdjustment"] = Gtk.Adjustment( self._data["track_volume"][1], 0, 100, 1, 1, 0 )
                #self.GUI["2instrument1volumeAdjustment"].connect( "value_changed", self.onTrackVolumeChanged, 0 )
                #self.GUI["2instrument1volumeSlider"] = Gtk.VScale(self.GUI["2instrument1volumeAdjustment"])
                #self.GUI["2instrument1volumeSlider"].set_draw_value(False)
                #self.GUI["2instrument1volumeSlider"].set_inverted(True)
                #self.GUI["2instrument1volumeSlider"].set_size_request( 30, -1 )
                #self.GUI["2instrument1volumeAdjustment"].connect( "value-changed", self.handleTrackVolume, 0 )
                self.GUI["2instrument1muteButton"] = ImageToggleButton(
                        'checkOff.png', 'checkOn.png')
                self.GUI["2instrument1muteButton"].connect("toggled",self.handlemuteButton,0)
                self.GUI["2instrument1muteButton"].connect("button-press-event",self.handlemuteButtonRightClick,0)
                self.GUI["2instrument1muteButton"].set_active(True)
                #self.GUI["2instrument1volBox"].pack_start( self.GUI["2instrument1volumeSlider"], True, True, 0 )
                #self.GUI["2instrument1volBox"].pack_start( self.GUI["2instrument1muteButton"], False, False, 5 )
                self.GUI["2instrument1Box"].pack_start( self.GUI["2instrument1volBox"], False, False, 0 )
                self.GUI["2instrument1Button"] = InstrumentButton( self, 0, Config.BG_COLOR )
                self.GUI["2instrument1Button"].connect('button-release-event',self.GUI["2instrumentPalette"].setBlock, 0)
                self.GUI["2instrument1Button"].setPrimary( self.GUI["2instrumentIcons"][self.trackInstrument[0].name] )
                self.GUI["2instrument1Box"].pack_start( self.GUI["2instrument1Button"], expand=True, fill=True, padding = 3 )
                self.GUI["2instrumentPanel"].add( self.GUI["2instrument1Box"] )
                # + + instrument 2 box
                self.GUI["2instrument2Box"] = formatRoundBox( RoundHBox(), Config.BG_COLOR )
                self.GUI["2instrument2Box"].set_size_request(-1, TRACK_SIZE)
                self.GUI["2instrument2volBox"] = Gtk.VBox()
                #self.GUI["2instrument2volumeAdjustment"] = Gtk.Adjustment( self._data["track_volume"][1], 0, 100, 1, 1, 0 )
                #self.GUI["2instrument2volumeAdjustment"].connect( "value_changed", self.onTrackVolumeChanged, 1 )
                #self.GUI["2instrument2volumeSlider"] = Gtk.VScale(self.GUI["2instrument2volumeAdjustment"])
                #self.GUI["2instrument2volumeSlider"].set_draw_value(False)
                #self.GUI["2instrument2volumeSlider"].set_inverted(True)
                #self.GUI["2instrument2volumeSlider"].set_size_request( 30, -1 )
                #self.GUI["2instrument2volumeAdjustment"].connect( "value-changed", self.handleTrackVolume, 1 )
                self.GUI["2instrument2muteButton"] = ImageToggleButton(
                        'checkOff.png', 'checkOn.png')
                self.GUI["2instrument2muteButton"].connect("toggled",self.handlemuteButton,1)
                self.GUI["2instrument2muteButton"].connect("button-press-event",self.handlemuteButtonRightClick,1)
                self.GUI["2instrument2muteButton"].set_active(True)
                #self.GUI["2instrument2volBox"].pack_start( self.GUI["2instrument2volumeSlider"], True, True, 0 )
                #self.GUI["2instrument2volBox"].pack_start( self.GUI["2instrument2muteButton"], False, False, 5 )
                self.GUI["2instrument2Box"].pack_start( self.GUI["2instrument2volBox"], False, False, 0 )
                self.GUI["2instrument2Button"] = InstrumentButton( self, 1, Config.BG_COLOR )
                self.GUI["2instrument2Button"].connect('button-release-event',self.GUI["2instrumentPalette"].setBlock, 1)
                self.GUI["2instrument2Button"].setPrimary( self.GUI["2instrumentIcons"][self.trackInstrument[1].name] )
                self.GUI["2instrument2Box"].pack_start( self.GUI["2instrument2Button"], expand=True,fill=True, padding =3 )
                self.GUI["2instrumentPanel"].add( self.GUI["2instrument2Box"] )
                # + + instrument 3 box
                self.GUI["2instrument3Box"] = formatRoundBox( RoundHBox(), Config.BG_COLOR )
                self.GUI["2instrument3Box"].set_size_request(-1, TRACK_SIZE)
                self.GUI["2instrument3volBox"] = Gtk.VBox()
                #self.GUI["2instrument3volumeAdjustment"] = Gtk.Adjustment( self._data["track_volume"][2], 0, 100, 1, 1, 0 )
                #self.GUI["2instrument3volumeAdjustment"].connect( "value_changed", self.onTrackVolumeChanged, 2 )
                #self.GUI["2instrument3volumeSlider"] = Gtk.VScale(self.GUI["2instrument3volumeAdjustment"])
                #self.GUI["2instrument3volumeSlider"].set_draw_value(False)
                #self.GUI["2instrument3volumeSlider"].set_inverted(True)
                #elf.GUI["2instrument3volumeSlider"].set_size_request( 30, -1 )
                #self.GUI["2instrument3volumeAdjustment"].connect( "value-changed", self.handleTrackVolume, 2 )
                self.GUI["2instrument3muteButton"] = ImageToggleButton(
                        'checkOff.png', 'checkOn.png')
                self.GUI["2instrument3muteButton"].connect("toggled",self.handlemuteButton,2)
                self.GUI["2instrument3muteButton"].connect("button-press-event",self.handlemuteButtonRightClick,2)
                self.GUI["2instrument3muteButton"].set_active(True)
                #self.GUI["2instrument3volBox"].pack_start( self.GUI["2instrument3volumeSlider"], True, True, 0 )
                #self.GUI["2instrument3volBox"].pack_start( self.GUI["2instrument3muteButton"], False, False, 5 )
                self.GUI["2instrument3Box"].pack_start( self.GUI["2instrument3volBox"], False, False, 0 )
                self.GUI["2instrument3Button"] = InstrumentButton( self, 2, Config.BG_COLOR )
                self.GUI["2instrument3Button"].connect('button-release-event',self.GUI["2instrumentPalette"].setBlock, 2)
                self.GUI["2instrument3Button"].setPrimary( self.GUI["2instrumentIcons"][self.trackInstrument[2].name] )
                self.GUI["2instrument3Box"].pack_start( self.GUI["2instrument3Button"], expand=True,fill=True, padding = 3 )
                self.GUI["2instrumentPanel"].add( self.GUI["2instrument3Box"] )
                # + + instrument 4 box
                self.GUI["2instrument4Box"] = formatRoundBox( RoundHBox(), Config.BG_COLOR )
                self.GUI["2instrument4Box"].set_size_request(-1, TRACK_SIZE)
                self.GUI["2instrument4volBox"] = Gtk.VBox()
                #self.GUI["2instrument4volumeAdjustment"] = Gtk.Adjustment( self._data["track_volume"][3], 0, 100, 1, 1, 0 )
                #self.GUI["2instrument4volumeAdjustment"].connect( "value_changed", self.onTrackVolumeChanged, 3 )
                #self.GUI["2instrument4volumeSlider"] = Gtk.VScale(self.GUI["2instrument4volumeAdjustment"])
                #self.GUI["2instrument4volumeSlider"].set_draw_value(False)
                #self.GUI["2instrument4volumeSlider"].set_inverted(True)
                #self.GUI["2instrument4volumeSlider"].set_size_request( 30, -1 )
                #self.GUI["2instrument4volumeAdjustment"].connect( "value-changed", self.handleTrackVolume, 3 )
                self.GUI["2instrument4muteButton"] = ImageToggleButton(
                        'checkOff.png', 'checkOn.png')
                self.GUI["2instrument4muteButton"].connect("toggled",self.handlemuteButton,3)
                self.GUI["2instrument4muteButton"].connect("button-press-event",self.handlemuteButtonRightClick,3)
                self.GUI["2instrument4muteButton"].set_active(True)
                #self.GUI["2instrument4volBox"].pack_start( self.GUI["2instrument4volumeSlider"], True, True, 0 )
                #self.GUI["2instrument4volBox"].pack_start( self.GUI["2instrument4muteButton"], False, False, 5 )
                self.GUI["2instrument4Box"].pack_start( self.GUI["2instrument4volBox"], False, False, 0 )
                self.GUI["2instrument4Button"] = InstrumentButton( self, 3, Config.BG_COLOR )
                self.GUI["2instrument4Button"].connect('button-release-event',self.GUI["2instrumentPalette"].setBlock, 3)
                self.GUI["2instrument4Button"].setPrimary( self.GUI["2instrumentIcons"][self.trackInstrument[3].name] )
                self.GUI["2instrument4Box"].pack_start( self.GUI["2instrument4Button"], expand=True,fill=True, padding = 3 )
                self.GUI["2instrumentPanel"].add( self.GUI["2instrument4Box"] )
                # + + drum box
                self.GUI["2drumBox"] = formatRoundBox( RoundHBox(), Config.BG_COLOR )
                self.GUI["2drumBox"].set_size_request(-1, DRUM_TRACK_SIZE)
                self.GUI["2drumVolBox"] = Gtk.VBox()
                self.GUI["2drumvolumeAdjustment"] = Gtk.Adjustment( self._data["track_volume"][4], 0, 100, 1, 1, 0 )
                self.GUI["2drumvolumeAdjustment"].connect( "value_changed", self.onTrackVolumeChanged, 4 )
                #self.GUI["2drumvolumeSlider"] = Gtk.VScale(self.GUI["2drumvolumeAdjustment"])
                #self.GUI["2drumvolumeSlider"].set_draw_value(False)
                #self.GUI["2drumvolumeSlider"].set_inverted(True)
                #self.GUI["2drumvolumeSlider"].set_size_request( 30, -1 )
                self.GUI["2drumvolumeAdjustment"].connect( "value-changed", self.handleTrackVolume, 4 )
                self.GUI["2drumMuteButton"] = ImageToggleButton(
                        'checkOff.png', 'checkOn.png')
                self.GUI["2drumMuteButton"].connect("toggled",self.handlemuteButton,4)
                self.GUI["2drumMuteButton"].connect("button-press-event",self.handlemuteButtonRightClick,4)
                self.GUI["2drumMuteButton"].set_active(True)
                #self.GUI["2drumVolBox"].pack_start( self.GUI["2drumvolumeSlider"], True, True, 0 )
                #self.GUI["2drumVolBox"].pack_start( self.GUI["2drumMuteButton"], False, False, 5 )
                self.GUI["2drumBox"].pack_start( self.GUI["2drumVolBox"], False, False, 0 )
                self.GUI["2drumButton"] = ImageToggleButton(
                        self.trackInstrument[4].name + '.png',
                        self.trackInstrument[4].name + '.png')
                self.GUI["2drumPalette"] = drumPalette(_('Track 5 Properties'), self, 4)
                self.GUI["2drumButton"].connect("toggled", self.pickDrum)
                self.GUI["2drumButton"].connect('button-release-event',self.GUI["2drumPalette"].setBlock)
                self.GUI["2drumBox"].add( self.GUI["2drumButton"] )
                self.GUI["2instrumentPanel"].add( self.GUI["2drumBox"] )
                self.GUI["2page"].add( self.GUI["2instrumentPanel"])
                # + track interface
                tracks_width = Gdk.Screen.width() - int(TRACK_SIZE * 1.25)
                self.trackInterface = TrackInterface( self.noteDB, self,
                        self.getScale, tracks_width)
                self.noteDB.addListener( self.trackInterface, TrackInterfaceParasite, True )
                self.trackInterface.set_size_request(tracks_width, -1)
                self.GUI["2page"].pack_start( self.trackInterface, False, True, 0)

            #------------------------------------------------------------------------
            # tune interface
            if 1:  # + tune interface
                self.GUI["2tuneScrolledWindow"] = HScrolledBox()
                self.tuneInterface = TuneInterface( self.noteDB, self, self.GUI["2tuneScrolledWindow"].get_adjustment() )
                self.noteDB.addListener( self.tuneInterface, TuneInterfaceParasite, True )
                self.GUI["2tuneScrolledWindow"].set_viewport( self.tuneInterface )
                self.tuneInterface.get_parent().set_shadow_type( Gtk.ShadowType.NONE )
                self.GUI["2tuneScrolledWindow"].set_size_request(-1,
                        Config.PAGE_THUMBNAIL_HEIGHT + style.DEFAULT_PADDING * 2)
                self.GUI["2tuneScrolledWindow"].modify_bg(Gtk.StateType.NORMAL,
                        style.Color(Config.TOOLBAR_BCK_COLOR).get_gdk_color())
                self.GUI["2main"].pack_start( self.GUI["2tuneScrolledWindow"], False, True, 0 )

            # set tooltips
            for key in self.GUI:
                if Tooltips.Edit.has_key(key):
                    self.GUI[key].set_tooltip_text(Tooltips.Edit[key])

            self.add( self.GUI["2main"] )

            self.skipCleanup = ""  # used when jumping between duplicate note/track


            # Popups
            TP.ProfileBegin("init_GUI::popups")
            self.GUI["9loopPopup"] = Gtk.Window(Gtk.WindowType.POPUP)
            self.GUI["9loopPopup"].move( 100, 100 )
            self.GUI["9loopPopup"].resize( 300, 100 )
            self.GUI["9loopPopup"].set_modal(True)
            self.GUI["9loopPopup"].connect("button-release-event", lambda w,e:self.GUI["2loopButton"].set_active(False) )
            self.GUI["9loopBox"] = formatRoundBox( RoundHBox(), Config.BG_COLOR )
            self.GUI["9loopAllOnce"] = Gtk.Button("AO")
            self.GUI["9loopBox"].add( self.GUI["9loopAllOnce"] )
            self.GUI["9loopAllRepeat"] = Gtk.Button("AR")
            self.GUI["9loopBox"].add( self.GUI["9loopAllRepeat"] )
            self.GUI["9loopSelectedOnce"] = Gtk.Button("SO")
            self.GUI["9loopBox"].add( self.GUI["9loopSelectedOnce"] )
            self.GUI["9loopSelectedRepeat"] = Gtk.Button("SR")
            self.GUI["9loopBox"].add( self.GUI["9loopSelectedRepeat"] )
            self.GUI["9loopPopup"].add(self.GUI["9loopBox"])
            TP.ProfileEnd("init_GUI::popups")

        #===================================================
        # begin initialization

        # keyboard variables
        self.kb_record = False
        self.kb_keydict = {}

        # playback params
        self.playing = False
        self.playSource = 'Page'
        self.currentpageId = 0
        self.playingTuneIdx = 0

        # timers
        self.playbackTimeout = False

        # FPS stuff
        self.fpsTotalTime = 0
        self.fpsFrameCount = 0
        self.fpsN = 100  # how many frames to average FPS over
        self.fpsLastTime = time.time()  # fps will be borked for the first few frames but who cares?

        self.context = -1 # invalidate
        self.contextTrackActive = False
        self.contextNoteActive = False

        init_data()   #above
        init_GUI()    #above

        # register for notification AFTER track and tune interfaces
        self.noteDB.addListener(self, page=True, note=True)

        self.csnd.setMasterVolume(self.getVolume())
        self.initTrackVolume()

        for tid in range(Config.NUMBER_OF_TRACKS):
            self.handleInstrumentChanged((tid, self.trackInstrument[tid]))

        instrumentsIds = []
        for inst in self.trackInstrument:
            instrumentsIds.append(inst.instrumentId)

        first = self.noteDB.addPage(-1, NoteDB.Page(4, instruments = instrumentsIds))
        self.displayPage(first)

        if not self.journalCalled:
            self.createNewTune(None)

        # Toolbar
        if Config.HAVE_TOOLBOX:
            #from sugar.graphics.toolbarbox import ToolbarButton

            common_buttons(self.activity.toolbox.toolbar, self)
            self._activity_toolbar = self.activity.toolbox.toolbar
            self._play_button = self.activity.toolbox.toolbar.playButton
            self._stop_button = self.activity.toolbox.toolbar.stopButton

            separator = Gtk.SeparatorToolItem()
            separator.props.draw = True
            separator.set_expand(False)
            self.activity.toolbox.toolbar.insert(separator, -1)

            self._generateToolbar = generateToolbar(self)
            self._generateToolbar.show()
            generate_toolbar_button = ToolbarButton(label=_('Generate'),
                                                page=self._generateToolbar,
                                                icon_name='diceB')
            generate_toolbar_button.show()
            self.activity.toolbox.toolbar.insert(generate_toolbar_button, -1)

            self._recordToolbar = recordToolbar(self)
            self._recordToolbar.show()
            record_toolbar_button = ToolbarButton(label=_('Record'),
                                                  page=self._recordToolbar,
                                                  icon_name='media-record')
            record_toolbar_button.show()
            self.activity.toolbox.toolbar.insert(record_toolbar_button, -1)
            self._record_button = self._recordToolbar.recordButton

            self._toolsToolbar = toolsToolbar(self)
            self._toolsToolbar.show()
            tools_toolbar_button = ToolbarButton(label=_('Tools'),
                                                 page=self._toolsToolbar,
                                                 icon_name='preferences-system')
            tools_toolbar_button.show()
            self.activity.toolbox.toolbar.insert(tools_toolbar_button, -1)

            separator = Gtk.SeparatorToolItem()
            separator.props.draw = False
            separator.set_expand(True)
            self.activity.toolbox.toolbar.insert(separator, -1)
        else:
            pass
            #self._mainToolbar = mainToolbar(self)
            #self._mainToolbar.show()
            #self.activity.toolbox.add_toolbar(_('Compose'), self._mainToolbar)
            #self._activity_toolbar = self._mainToolbar
            #self._play_button = self._mainToolbar.playButton
            #self._stop_button = self._mainToolbar.stopButton

            #self._toolsToolbar = toolsToolbar(self)
            #self._toolsToolbar.show()
            #self.activity.toolbox.add_toolbar(_('Tools'),
            #                                  self._toolsToolbar)
            #self._record_button = self._toolsToolbar.recordButton

            #self.activity.toolbox.set_current_toolbar(1)

        self.show_all()  #gtk command

        self.setContext(CONTEXT.PAGE)

        self.audioRecordWidget = None

    def createNewTune(self, widget, data=None):
        self.createNewTune3()

    def createNewTune3(self):

        if self.playing == True:
            self.handleStop()

        self.tuneInterface.selectPages(self.noteDB.getTune())

        beats = random.randint(3,6)
        stream = []
        for page in self.noteDB.getTune():
            stream += [ page, beats ]
        if len(stream):
            self.noteDB.updatePages( [ PARAMETER.PAGE_BEATS, len(stream)//2 ] + stream )

        orch = self.newOrchestra()

        for i in orch:
            if i.kit == None:
                self.csnd.load_instrument(i.name)
            else:
                self.csnd.load_drumkit(i.name)

        instrumentsIds = []
        for inst in orch:
            instrumentsIds.append(inst.instrumentId)

        self.pageDelete(-1, instruments = instrumentsIds)

        initTempo = random.randint(60, 132)
        self._data['tempo'] = initTempo

        formsUsed = []
        for section in self.tuneForm:
            if section[0] not in formsUsed:
                param = self.chooseGenParams()
                self.tuneInterface.selectPages(self.noteDB.getTune())
                if not formsUsed:
                    for i in range(section[2]-1):
                        self.pageAdd(instruments = instrumentsIds)
                else:
                    for i in range(section[2]):
                        self.pageAdd(instruments = instrumentsIds)
                formsUsed.append(section[0])

                self.tuneInterface.selectPages(self.noteDB.getTune()[-section[2]:])
                self.generateMode = 'page'
                self.generate( GenerationParameters( density = param[0], rythmRegularity = param[1], step = param[2], pitchRegularity = param[3], articule = param[4], silence = param[5], pattern = param[6], scale = param[7]), section[2] )
            else:
                pageOffset = 0
                pageIds = []
                firstPos = [i[0] for i in self.tuneForm].index(section[0])
                if firstPos == 0:
                    pageOffset = 0
                else:
                    for i in range(firstPos):
                        pageOffset += self.tuneForm[i][2]
                for i in range(section[2]):
                    pageIds.append(self.noteDB.getTune()[pageOffset + i])
                after = self.noteDB.getTune()[-1]
                self.displayPage(self.noteDB.getTune()[pageOffset])
                self.tuneInterface.selectPages(self.noteDB.getTune())
                self.pageDuplicate(-1, pageIds)

        self.tuneInterface.selectPages(self.noteDB.getTune())
        self.displayPage(self.noteDB.getTune()[0])


    def newOrchestra(self):
        stringsPickup = []
        windsPickup = []
        keyboardPickup = []
        fxPickup = []
        drumsPickup = ["drum1kit", "drum2kit", "drum3kit", "drum4kit", "drum5kit"]
        for name in self.instrumentDB.instNamed.keys():
            if self.instrumentDB.instNamed[name].category == 'strings' and self.instrumentDB.instNamed[name].name != 'violin':
                stringsPickup.append(name)
            elif self.instrumentDB.instNamed[name].category == 'winds' and self.instrumentDB.instNamed[name].name != 'didjeridu':
                windsPickup.append(name)
            elif self.instrumentDB.instNamed[name].category == 'keyboard' or self.instrumentDB.instNamed[name].category == 'percussions' and not name.startswith('drum'):
                if self.instrumentDB.instNamed[name].name != 'zap' and self.instrumentDB.instNamed[name].name != 'cling':
                    keyboardPickup.append(name)
        return [
                    self.instrumentDB.instNamed[random.choice(stringsPickup)],
                    self.instrumentDB.instNamed[random.choice(stringsPickup)],
                    self.instrumentDB.instNamed[random.choice(windsPickup)],
                    self.instrumentDB.instNamed[random.choice(keyboardPickup)],
                    self.instrumentDB.instNamed[random.choice(drumsPickup)] ]

    def chooseGenParams(self):
        choose = [random.randint(0,16) for x in range(4)]
        density = [GenerationConstants.RYTHM_DENSITY_BANK[i] for i in choose]
        rytReg = [GenerationConstants.RYTHM_REGU_BANK[i] for i in choose]
        step = [GenerationConstants.PITCH_STEP_BANK[i] for i in choose]
        pitReg = [GenerationConstants.PITCH_REGU_BANK[i] for i in choose]
        dur = [GenerationConstants.DURATION_BANK[i] for i in choose]
        silence = [GenerationConstants.SILENCE_BANK[i] for i in choose]
        pattern = [GenerationConstants.PATTERN_BANK[i] for i in choose]
        scale = random.randint(0,6)
        return [density, rytReg, step, pitReg, dur, silence, pattern, scale]

    def onActivate(self, arg):
        # whatever needs to be done on initialization
        self.csnd.loopPause()
        self.csnd.loopClear()
        for n in self.noteDB.getNotes( ):
            self.csnd.loopPlay(n, 0)  # adds all notes to c client in inactive state


    def onDeactivate(self):
        # clean up things like popups etc
        self.csnd.loopPause()
        self.csnd.loopClear()


    def updateFPS(self):
        t = time.time()
        dt = t - self.fpsLastTime
        self.fpsLastTime = t
        self.fpsTotalTime += dt
        self.fpsFrameCount += 1
        if self.fpsFrameCount == self.fpsN:
            fps = self.fpsN/self.fpsTotalTime
            avgMS = 1000/fps
            fps = "FPS %d ms %.2f" % (fps, avgMS)
            #self.fpsText.set_text(fps )
            if (Config.DEBUG > 2):  print fps
            self.fpsTotalTime = 0
            self.fpsFrameCount = 0

    #=========================================================
    # Popup Windows

    def doneGenerationPopup(self):
        if self.GUI["2pageGenerateButton"].get_active():
            self.GUI["2pageGenerateButton"].set_active( False )
        if self.GUI["2trackGenerateButton"].get_active():
            self.GUI["2trackGenerateButton"].set_active( False )

    def donePropertiesPopup(self):
        if self.GUI["2pagePropertiesButton"].get_active():
            self.GUI["2pagePropertiesButton"].set_active( False )
        if self.GUI["2trackPropertiesButton"].get_active():
            self.GUI["2trackPropertiesButton"].set_active( False )
        if self.GUI["2notePropertiesButton"].get_active():
            self.GUI["2notePropertiesButton"].set_active( False )

    def cancelPopup(self, w, event, popup):
        popup.hide()


    def handleLoopButton(self, w):
        if w.get_active(): self.GUI["9loopPopup"].show_all()
        else: self.GUI["9loopPopup"].hide()

    #-----------------------------------
    # playback functions
    #-----------------------------------

    def updatePageSelection(self, selectedIds):
        if not self.playing:
            return

        if self.playScope == "All":
            return

        if self.displayedPage in selectedIds:
            startPage = self.displayedPage
        else:
            startPage = selectedIds[0]

        self._playPages(selectedIds, startPage, self.trackInterface.getPlayhead())

    def updatePagesPlaying(self):
        if not self.playing:
            return

        curTick = self.csnd.loopGetTick()

        pageTick = self.page_onset[self.displayedPage]
        if curTick < pageTick:
            pageTick = 0
            startPage = self.pages_playing[0]
        else:
            startPage = self.displayedPage

        localTick = curTick - pageTick

        self._playPages(self.tuneInterface.getSelectedIds(), startPage, localTick)

    def handleAudioRecord(self, widget, data=None):
        if widget.get_active() == True:
            self.audioRecordWidget = widget
            self.audioRecordTick = -1
        else:
            self.audioRecordWidget = None

    def handlePlay(self, widget = None):
        if widget:
            pass

        if self.audioRecordWidget:
            filename = Config.TMP_DIR + "/perf.wav"
            self.csnd.inputMessage( Config.CSOUND_RECORD_PERF % filename)
            time.sleep( 0.01 )

        if self.playScope == "All":
            toPlay = self.noteDB.getTune()
        else:
            toPlay = self.tuneInterface.getSelectedIds()

        self._playPages(toPlay, self.displayedPage, self.trackInterface.getPlayhead())

        self.playing = True

    def handlePlayPause_cb(self, widget, data=None):
        if widget.get_active():
            self.handlePlay(widget)
            self._activity_toolbar.handler_block(
                self._activity_toolbar.playButtonHandler)
            self._play_button.set_active(True)
            self._activity_toolbar.handler_unblock(
                self._activity_toolbar.playButtonHandler)
            widget.set_icon_widget(self._activity_toolbar.pauseButtonImg)
            self._play_button.set_icon_widget(
                self._activity_toolbar.pauseButtonImg)
        else:
            self.handleStop(widget, False)
            self._activity_toolbar.handler_block(
                self._activity_toolbar.playButtonHandler)
            self._play_button.set_active(False)
            self._activity_toolbar.handler_unblock(
                self._activity_toolbar.playButtonHandler)
            widget.set_icon_widget(self._activity_toolbar.playButtonImg)
            self._play_button.set_icon_widget(
                self._activity_toolbar.playButtonImg)

    def handleStop_cb(self, widget, data=None):
        self._play_button.set_active(False)
        self.handleStop(widget, True)
        if self._record_button.get_active():
            self._record_button.set_active(False)

    def handleRecord_cb(self, widget, data=None):
        if widget.get_active():
            self._play_button.set_active(False)
        self.handleAudioRecord(widget, data)
        if widget.get_active():
            GObject.timeout_add(500, self._startAudioRecord)

    def _startAudioRecord(self):
        self._play_button.set_active(True)
        return False

    def _playPages(self, pages, startPage, startTick):

        self.pages_playing = pages[:]

        trackset = set([i for i in range(Config.NUMBER_OF_TRACKS) if self.trackActive[i]])

        numticks = 0
        self.page_onset = {}
        for pid in self.pages_playing:
            self.page_onset[pid] = numticks
            numticks += self.noteDB.getPage(pid).ticks

        # check for a second instrument on melodic tracks
        stream = []
        for page in self.pages_playing:
            for track in trackset:
                if track != self.drumIndex:
                    if self.trackInstrument2[track] != None:
                        if len(self.noteDB.getNotesByTrack(page, track)):
                            stream += [ page, track, NoteDB.PARAMETER.INSTRUMENT2, len(self.noteDB.getNotesByTrack(page, track)) ]
                            for n in self.noteDB.getNotesByTrack(page, track):
                                stream += [ n.id, self.trackInstrument2[track].instrumentId ]
        if len(stream):
            self.noteDB.updateNotes(stream + [-1])

        self.csnd.loopClear()
        for page in self.pages_playing:
            for track in trackset:
                for n in self.noteDB.getNotesByTrack(page, track):
                    self.csnd.loopPlay(n, 1)
                    self.csnd.loopUpdate(n, NoteDB.PARAMETER.ONSET, n.cs.onset + self.page_onset[n.page] , 1)

        self.csnd.loopSetNumTicks(numticks)

        self.csnd.loopSetTick(self.page_onset[startPage] + startTick)
        self.csnd.setTempo(self._data['tempo'])
        if (Config.DEBUG > 3): print "starting from tick", startTick, 'at tempo', self._data['tempo']
        self.csnd.loopStart()

        if not self.playbackTimeout:
            self.playbackTimeout = GObject.timeout_add(50, self.onTimeout)



    def handleStop(self, widget = None, rewind = True):

        if widget:
            pass

        if self.audioRecordWidget:
            filename = Config.TMP_DIR + "/perf.wav"
            self.csnd.inputMessage( Config.CSOUND_STOP_RECORD_PERF % filename)
            time.sleep(0.01)

        if self.playbackTimeout:
            GObject.source_remove(self.playbackTimeout)
            self.playbackTimeout = False

        self.csnd.loopPause()
        self.csnd.loopDeactivate()

        if self.audioRecordWidget:
            time.sleep(4)
            self.csnd.__del__()
            time.sleep(0.5)
            tmp_ogg = os.path.join(Config.TMP_DIR, "perf.ogg")

            command = "gst-launch-0.10 filesrc location=" + Config.TMP_DIR + "/perf.wav ! wavparse ! audioconvert ! vorbisenc ! oggmux !  filesink location=" + tmp_ogg
            command2 = "rm " + Config.TMP_DIR + "/perf.wav"
            OS.system(command)
            OS.system(command2)

            from datetime import datetime
            title = '%s %s.ogg' % (self.activity.get_title(),
                    datetime.now().isoformat(' '))

            jobject = datastore.create()
            jobject.metadata['title'] = title
            jobject.metadata['keep'] = '1'
            jobject.metadata['mime_type'] = 'audio/ogg'
            jobject.file_path = tmp_ogg
            datastore.write(jobject)

            os.remove(tmp_ogg)
            self.audioRecordWidget.set_active(False)
            self.audioRecordWidget = None

            self.csnd.__init__()
            time.sleep(0.1)
            self.csnd.connect(True)
            time.sleep(0.1)
            self.waitToSet()
            self.csnd.load_instruments()
            self.GUI["2recordButton"].set_active(False)
        self.playing = False

        if rewind: self.handleRewind()

    def handleRewind(self, widget = None):
        if self.playScope == "All": id = self.noteDB.getPageByIndex(0)
        else: id = self.tuneInterface.getFirstSelected()
        self.trackInterface.setPlayhead( 0 )
        self.displayPage( id )

    def handleClose(self,widget):
        self.activity.close()

    def onTimeout(self):
        self.updateFPS()

        curTick = self.csnd.loopGetTick()

        pageTick = self.page_onset[self.displayedPage]
        if curTick < pageTick:
            pageTick = 0
            ind = 0
        else:
            ind = self.pages_playing.index(self.displayedPage)

        localTick = curTick - pageTick
        pageLength = self.noteDB.getPage(self.pages_playing[ind]).ticks
        max = len(self.pages_playing)
        while localTick > pageLength:
            ind += 1
            if ind == max: ind = 0
            localTick -= pageLength
            pageLength = self.noteDB.getPage(self.pages_playing[ind]).ticks

        self.trackInterface.setPlayhead(localTick)

        if self.pages_playing[ind] != self.displayedPage:
            if ind + 1 < max: predraw = self.pages_playing[ind+1]
            else: predraw = self.pages_playing[0]
            self._displayPage( self.pages_playing[ind], predraw )
        else:
            self.trackInterface.predrawPage()

        if self.audioRecordWidget:
            if self.audioRecordTick > curTick:  # we've looped around
                self.handleStop()
            else:
                self.audioRecordTick = curTick


        return True

    def onMuteTrack(self, widget, trackId):
        self._data['track_mute'][trackId] = not self._data['track_mute'][trackId]
        #if self._data['track_mute'][trackId]:
            #self.noteLooper.setMute( trackId, 0.0 )
        #else:
            #self.noteLooper.setMute( trackId, 1.0 )

    def onTrackVolumeChanged(self, widget, trackId):
        v =  widget.get_value() / 100.0
        self._data['track_volume'][trackId] = v
        #self.noteLooper.setVolume( trackId, v )

    def clearInstrument(self, id, primary = True):
        btn = self.GUI["2instrument%dButton" % (id+1)]
        if primary:
            if self.trackInstrument2[id] == None:
                return
            self.handleInstrumentChanged((id, self.trackInstrument2[id]), True)
            self.handleInstrumentChanged((id, None), False)
            btn.setPrimary(self.GUI["2instrumentIcons"][self.trackInstrument[id].name])
            btn.setSecondary(None)
        else:
            self.handleInstrumentChanged((id, None), False)
            btn.setSecondary(None)
            pages = self.tuneInterface.getSelectedIds()
            self.noteDB.setInstrument2(pages, id, -1)

    # data is tuple ( trackId, instrumentName )
    def handleInstrumentChanged(self, data, primary = True):
        (id, instrument) = data
        if primary:
            self.trackInstrument[id] = instrument
        else:
            self.trackInstrument2[id] = instrument

        if instrument:
            if instrument.kit == None:
                self.csnd.load_instrument(instrument.name)
            else:
                self.csnd.load_drumkit(instrument.name)

        if primary: # TODO handle secondary instruments properly
            if (Config.DEBUG > 3): print "handleInstrumentChanged", id, instrument.name, primary

            pages = self.tuneInterface.getSelectedIds()
            self.noteDB.setInstrument( pages, id, instrument.instrumentId )

    def getScale(self):
        return self.scale

    def handleVolume(self, widget):
        self._data["volume"] = round(widget.get_value())
        self.csnd.setMasterVolume(self._data["volume"])
        img = min(3,int(4*self._data["volume"]/100)) # volume 0-3
        #self.GUI["2volumeImage"].set_from_file(imagefile('volume' + str(img) + '.png'))

    def initTrackVolume(self):
        for i in range(Config.NUMBER_OF_TRACKS):
            self.csnd.setTrackVolume(self._data["track_volume"][i], i)

    def handleTrackVolume(self, widget = None, track = None):
        self._data["track_volume"][track] = round( widget.get_value() )
        self.csnd.setTrackVolume(self._data["track_volume"][track], track)

    def getTrackInstrument(self, track):
        return self.trackInstrument[track]

    def getTrackVolume(self, track):
        return self._data["track_volume"][track]

    def handleTempo(self, widget):
        self._data['tempo'] = round(widget.get_value())
        img = min(7,int(8*(self._data["tempo"] - widget.get_lower())/(widget.get_upper() - widget.get_lower())))+1  # tempo 1-8
        #self.GUI["2tempoImage"].set_from_file(imagefile('tempo' + str(img) + '.png'))
        if self.playing:
            self.csnd.setTempo(self._data['tempo'])

    def getTool(self):
        if self.GUI["2toolPointerButton"].get_active(): return "default"
        else: return "draw"

    def handleKeyboardRecordButton(self, widget, data=None):
        self.kb_record = widget.get_active()

    def pickInstrument(self, widget, num, primary = True):
        self.last_clicked_instTrackID = num
        self.last_clicked_instPrimary = primary

        if primary or self.trackInstrument2[num] == None:
            instrument = self.trackInstrument[num]
        else:
            instrument = self.trackInstrument2[num]

        self.GUI["2instrumentPalette"].setInstrument(instrument)

    def cancelInstrumentSelection(self):
        self.GUI["9instrumentPopup"].hide()

    def donePickInstrument(self, instrumentName):
        self.handleInstrumentChanged( (self.last_clicked_instTrackID, self.instrumentDB.instNamed[instrumentName]), self.last_clicked_instPrimary )
        btn = self.GUI["2instrument%dButton" % (self.last_clicked_instTrackID+1)]
        if self.last_clicked_instPrimary:
            btn.setPrimary( self.GUI["2instrumentIcons"][instrumentName] )
        else:
            btn.setSecondary( self.GUI["2instrumentIcons"][instrumentName] )
        #self.GUI["9instrumentPopup"].hide()


    def pickDrum(self, widget , data = None):
        if widget.get_active():
            self.GUI['2drumPalette'].setDrum(self.trackInstrument[Config.NUMBER_OF_TRACKS-1].name)

    def cancelDrumSelection(self):
        self.GUI["2drumButton"].set_active(False)

    def donePickDrum(self, drumName):
        self.handleInstrumentChanged((self.drumIndex, self.instrumentDB.instNamed[drumName]))
        self.GUI["2drumButton"].setImage("main", self.GUI["2instrumentIcons"][drumName])
        self.GUI["2drumButton"].setImage("alt", self.GUI["2instrumentIcons"][drumName])
        self.GUI["2drumButton"].set_active(False)

    def playInstrumentNote(self, instrumentName, secs_per_tick = 0.025):
        self.csnd.play(
                    CSoundNote( onset = 0,
                             pitch = 36,
                             amplitude = 1,
                             pan = 0.5,
                             duration = 20,
                             trackId = 1,
                             instrumentId = self.instrumentDB.instNamed[instrumentName].instrumentId,
                             reverbSend = 0),
                    secs_per_tick)

    def handlemuteButton(self,widget,track):
        if widget.get_active():
            self.trackActive[track] = True
        else:
            self.trackActive[track] = False
        self.updatePagesPlaying()

    def handlemuteButtonRightClick(self,widget,event,track):
        if event.button == 3:
            widget.set_active(True)
            #if the other tracks are inactive
            if self.trackActive.count(False) == Config.NUMBER_OF_TRACKS - 1:
                for i in range(Config.NUMBER_OF_TRACKS):
                    if i == 4:
                        #self.GUI["2drumMuteButton"].set_active(True)
                        self.GUI["2drumPalette"].muteButton.set_active(True)
                    else:
                        #self.GUI["2instrument" + str(i+1) + "muteButton"].set_active(True)
                        self.GUI["2instrument" + str(i+1) + "Palette"].muteButton.set_active(True)
            else:
                for i in range(Config.NUMBER_OF_TRACKS):
                    if i != track:
                        if i == 4:
                            #self.GUI["2drumMuteButton"].set_active(False)
                            self.GUI["2drumPalette"].muteButton.set_active(False)
                        else:
                            #self.GUI["2instrument" + str(i+1) + "muteButton"].set_active(False)
                            self.GUI["2instrument" + str(i+1) + "Palette"].muteButton.set_active(False)
            self.updatePagesPlaying()

    #-----------------------------------
    # generation functions
    #-----------------------------------

    def recompose(self, algo, params, nPagesCycle = 4):
        if self.generateMode == "track":
            if self.trackSelected == [ 0 for i in range(Config.NUMBER_OF_TRACKS) ]:
                newtracks = set(range(Config.NUMBER_OF_TRACKS))
            else:
                newtracks = set([i for i in range(Config.NUMBER_OF_TRACKS) if self.trackSelected[i]])
            newpages  = self.tuneInterface.getSelectedIds()
        else:  # page mode
            newtracks = set(range(Config.NUMBER_OF_TRACKS))
            newpages = self.tuneInterface.getSelectedIds()

        dict = {}
        for t in newtracks:
            dict[t] = {}
            for p in newpages:
                dict[t][p] = self.noteDB.getCSNotesByTrack(p, t)

        beatsOfPages = {}
        for pageId in newpages:
            beatsOfPages[pageId] = self.noteDB.pages[pageId].beats

        instruments = self.noteDB.getInstruments(newpages)

        #[ i.name for i in self.trackInstrument ],
        algo(
                params,
                self._data['track_volume'][:],
                instruments,
                self._data['tempo'],
                beatsOfPages,
                newtracks,
                newpages,
                dict, nPagesCycle)

        # filter & fix input ...WTF!?
        for track in dict:
            for page in dict[track]:
                for note in dict[track][page]:
                    intdur = int(note.duration)
                    note.duration = intdur
                    note.pageId = page
                    note.trackId = track

        # prepare the new notes
        newnotes = []
        for tid in dict:
            for pid in dict[tid]:
                newnotes += dict[tid][pid]

        # delete the notes and add the new
        self.noteDB.deleteNotesByTrack( newpages, newtracks )

        stream = []
        for page in newpages:
            for track in newtracks:
                stream += [ page, track, len(dict[track][page]) ]
                stream += dict[track][page]
        stream += [-1]
        self.noteDB.addNotes( stream )

    def generate(self, params, nPagesCycle = 4):
        self.recompose( generator1, params, nPagesCycle)

    #=======================================================
    # Clipboard Functions

    def getClipboardArea(self, page = -1):
        if page == -1: page = self.displayedPage
        ids = self.tuneInterface.getSelectedIds()
        return self.noteDB.getClipboardArea(ids.index(page))

    def pasteClipboard(self, offset, trackMap):
        pages = self.tuneInterface.getSelectedIds()
        instrumentMap = {}
        for t in trackMap:
            if t != trackMap[t]: instrumentMap[t] = self.trackInstrument[t].instrumentId
        return self.noteDB.pasteClipboard( pages, offset, trackMap, instrumentMap )

    def cleanupClipboard(self):
        self.trackInterface.donePaste()


    #=======================================================
    # Note Functions

    def noteProperties(self, widget):
        if widget.get_active():
            ids = self.trackInterface.getSelectedNotes()
            notes = { self.displayedPage: {} }
            for t in range(Config.NUMBER_OF_TRACKS):
                if len(ids[t]):
                    notes[self.displayedPage][t] = [ self.noteDB.getNote( self.displayedPage, t, id ) for id in ids[t] ]

            self.propertiesPanel.setContext("note", self.generationPanel.scale, notes = notes )
            winLoc = self.parent.window.get_position()
            balloc = self.GUI["2contextBox"].get_allocation()
            walloc = self.GUI["9propertiesPopup"].get_allocation()
            if walloc.height != 1: # hack to deal with showing the window before first allocation T_T
                self.GUI["9propertiesPopup"].move( balloc.x + winLoc[0] - 30, balloc.y - walloc.height + winLoc[1] )
            else:
                self.GUI["9propertiesPopup"].move(0, 2048) # off the screen
            self.GUI["9propertiesPopup"].show()
            if walloc.height == 1:
                walloc = self.GUI["9propertiesPopup"].get_allocation()
                self.GUI["9propertiesPopup"].move( balloc.x + winLoc[0] - 30, balloc.y - walloc.height + winLoc[1] )
        else:
            self.GUI["9propertiesPopup"].hide()

    def noteDelete(self):
        ids = self.trackInterface.getSelectedNotes()
        stream = []
        for t in range(Config.NUMBER_OF_TRACKS):
            N = len(ids[t])
            if not N: continue
            stream += [ self.displayedPage, t, N ] + ids[t]
        if len(stream):
            self.noteDB.deleteNotes( stream + [-1] )

    def noteDuplicate(self):
        ids = self.trackInterface.getSelectedNotes()
        stream = []
        for t in range(Config.NUMBER_OF_TRACKS):
            N = len(ids[t])
            if not N: continue
            stream += [ self.displayedPage, t, N ] + ids[t]
        if len(stream):
            self.skipCleanup = "note"
            self.skipCleanup = ""
            self.noteDB.notesToClipboard( stream + [-1] )
            self.trackInterface.setInterfaceMode("paste_notes")
            return True
        return False

    def noteDuplicateWidget( self, widget ):
        if widget.get_active():
            if self.noteDuplicate():  # duplicate succeeded
                return
            # cancel duplicate
            widget.set_active(False)
            self.trackInterface.setInterfaceMode("tool")
        else:
            self.trackInterface.setInterfaceMode("tool")

    def noteOnset( self, step ):
        self.trackInterface.noteStepOnset( step )

    def notePitch( self, step ):
        # TODO
        return

    def noteDuration( self, step ):
        # TODO
        return

    def noteVolume( self, step ):
        # TODO
        return

    #=======================================================
    # Track Functions

    def toggleTrack(self, trackN, exclusive):
        if exclusive:
            for i in range(Config.NUMBER_OF_TRACKS):
                if self.trackSelected[i]:
                    self.trackSelected[i] = False
                    self.trackInterface.trackToggled( i )
                    self.tuneInterface.trackToggled( i )
            self.trackSelected[trackN] = True
            self.trackInterface.trackToggled( trackN )
            self.tuneInterface.trackToggled( trackN )
            self.setContextState( CONTEXT.TRACK, True )
            self.setContext( CONTEXT.TRACK )
        else:
            self.trackSelected[trackN] = not self.trackSelected[trackN]
            self.trackInterface.trackToggled( trackN )
            self.tuneInterface.trackToggled( trackN )
            trackSelected = False
            for i in range(Config.NUMBER_OF_TRACKS):
                if self.trackSelected[i]:
                    self.setContextState(CONTEXT.TRACK, True)
                    self.setContext(CONTEXT.TRACK)
                    trackSelected = True
                    break
            if not trackSelected:
                self.setContextState(CONTEXT.TRACK, False)

    def setTrack(self, trackN, state):
        if self.trackSelected[trackN] != state:
            self.trackSelected[trackN] = state
            self.trackInterface.trackToggled( trackN )

    def clearTracks(self):
        for i in range(Config.NUMBER_OF_TRACKS):
            if self.trackSelected[i]:
                self.trackSelected[i]= False
                self.trackInterface.trackToggled( i )
                self.tuneInterface.trackToggled( i )

        self.setContextState(CONTEXT.TRACK, False)

    def getTrackSelected(self, trackN):
        return self.trackSelected[trackN]

    def trackGenerate(self, widget):
        if widget.get_active():
            self.generateMode = "track"
            winLoc = self.parent.window.get_position()
            balloc = self.GUI["2contextBox"].get_allocation()
            walloc = self.GUI["9generationPopup"].get_allocation()
            if walloc.height != 1: # hack to make deal with showing the window before first allocation T_T
                self.GUI["9generationPopup"].move( balloc.x + winLoc[0], balloc.y - walloc.height + winLoc[1] )
            else:
                self.GUI["9generationPopup"].move(0, 2048) # off the screen
            self.GUI["9generationPopup"].show()
            if walloc.height == 1:
                walloc = self.GUI["9generationPopup"].get_allocation()
                self.GUI["9generationPopup"].move( balloc.x + winLoc[0], balloc.y - walloc.height + winLoc[1] )
        else:
            self.GUI["9generationPopup"].hide()


    def trackProperties(self, widget):
        if widget.get_active():
            self.propertiesPanel.setContext( "track", self.generationPanel.scale, self.tuneInterface.getSelectedIds(), [ i for i in range(Config.NUMBER_OF_TRACKS) if self.trackSelected[i] ] )
            winLoc = self.parent.window.get_position()
            balloc = self.GUI["2contextBox"].get_allocation()
            walloc = self.GUI["9propertiesPopup"].get_allocation()
            if walloc.height != 1: # hack to make deal with showing the window before first allocation T_T
                self.GUI["9propertiesPopup"].move( balloc.x + winLoc[0] - 30, balloc.y - walloc.height + winLoc[1] )
            else:
                self.GUI["9propertiesPopup"].move(0, 2048) # off the screen
            self.GUI["9propertiesPopup"].show()
            if walloc.height == 1:
                walloc = self.GUI["9propertiesPopup"].get_allocation()
                self.GUI["9propertiesPopup"].move( balloc.x + winLoc[0] - 30, balloc.y - walloc.height + winLoc[1] )
        else:
            self.GUI["9propertiesPopup"].hide()

    def trackDelete(self, pageIds = -1, trackIds = -1):

        if pageIds == -1: pageIds = self.tuneInterface.getSelectedIds()
        if trackIds == -1: trackIds = [ i for i in range(Config.NUMBER_OF_TRACKS) if self.trackSelected[i] ]

        self.noteDB.deleteNotesByTrack( pageIds, trackIds )

    def trackDuplicate(self, pageIds = -1, trackIds = -1):

        if pageIds == -1: pageIds = self.tuneInterface.getSelectedIds()
        if trackIds == -1: trackIds = [ i for i in range(Config.NUMBER_OF_TRACKS) if self.trackSelected[i] ]

        if len(trackIds):
            self.skipCleanup = "track"
            self.skipCleanup = ""
            self.noteDB.tracksToClipboard(pageIds, trackIds)
            self.trackInterface.setInterfaceMode("paste_tracks")
            return True
        return False

    def trackDuplicateWidget(self, widget):
        if widget.get_active():
            if self.trackDuplicate():  # duplicate succeeded
                return
            # cancel duplicate
            widget.set_active(False)
            self.trackInterface.setInterfaceMode("tool")
        else:
            self.trackInterface.setInterfaceMode("tool")

    #-----------------------------------
    # tune/page functions
    #-----------------------------------

    def displayPage(self, pageId, nextId = -1):
        if self.playing:
            if self.displayedPage != pageId and pageId in self.pages_playing:
                self.csnd.loopSetTick( self.page_onset[pageId] )

        self._displayPage(pageId, nextId)


    # only called locally!
    def _displayPage(self, pageId, nextId = -1):

        self.displayedPage = pageId

        page = self.noteDB.getPage(pageId)
        for i in range(Config.NUMBER_OF_TRACKS):
            if self.trackInstrument[i].instrumentId != page.instruments[i]:
                self.trackInstrument[i] = self.instrumentDB.instId[page.instruments[i]]
                if i == Config.NUMBER_OF_TRACKS-1:
                    btn = self.GUI["2drumButton"]
                    btn.setImage( "main", self.GUI["2instrumentIcons"][self.trackInstrument[i].name] )
                    btn.setImage( "alt", self.GUI["2instrumentIcons"][self.trackInstrument[i].name] )
                else:
                    btn = self.GUI["2instrument%dButton"%(i+1)]
                    btn.setPrimary( self.GUI["2instrumentIcons"][self.trackInstrument[i].name] )
                    if self.trackInstrument2[i] != None:
                        btn.setSecondary( self.GUI["2instrumentIcons"][self.trackInstrument2[i].name] )
                    else:
                        btn.setSecondary( None )
        self.tuneInterface.displayPage( pageId )
        self.trackInterface.displayPage( pageId, nextId )

    def predrawPage(self, pageId):
        if self.playbackTimeout: return  # we're playing, predrawing is already handled
        if self.trackInterface.setPredrawPage( pageId ):  # page needs to be drawn
            self.trackInterface.predrawPage()

    def abortPredrawPage(self):
        self.trackInterface.abortPredrawPage()

    def pageGenerate(self, widget):
        if widget.get_active():
            self.generateMode = "page"
            winLoc = self.parent.window.get_position()
            balloc = self.GUI["2contextBox"].get_allocation()
            walloc = self.GUI["9generationPopup"].get_allocation()
            if walloc.height != 1: # hack to make deal with showing the window before first allocation T_T
                self.GUI["9generationPopup"].move( balloc.x + winLoc[0], balloc.y - walloc.height + winLoc[1] )
            else:
                self.GUI["9generationPopup"].move(0, 2048) # off the screen
            self.GUI["9generationPopup"].show()
            if walloc.height == 1:
                walloc = self.GUI["9generationPopup"].get_allocation()
                self.GUI["9generationPopup"].move(balloc.x + winLoc[0], balloc.y - walloc.height + winLoc[1])
        else:
            self.GUI["9generationPopup"].hide()

    def setPageGenerateMode(self, mode):
        self.generateMode = mode

    def pageProperties(self, widget):
        if widget.get_active():
            self.propertiesPanel.setContext("page", self.generationPanel.scale, self.tuneInterface.getSelectedIds())
            winLoc = self.parent.window.get_position()
            balloc = self.GUI["2contextBox"].get_allocation()
            walloc = self.GUI["9propertiesPopup"].get_allocation()
            if walloc.height != 1:  # hack to make deal with showing the window before first allocation T_T
                self.GUI["9propertiesPopup"].move( balloc.x + winLoc[0] - 100, balloc.y - walloc.height + winLoc[1] )
            else:
                self.GUI["9propertiesPopup"].move(0, 2048)  # off the screen
            self.GUI["9propertiesPopup"].show()
            if walloc.height == 1:
                walloc = self.GUI["9propertiesPopup"].get_allocation()
                self.GUI["9propertiesPopup"].move( balloc.x + winLoc[0] - 100, balloc.y - walloc.height + winLoc[1] )
        else:
            self.GUI["9propertiesPopup"].hide()

    def pageDelete(self, pageIds = -1, instruments = False):

        if pageIds == -1:
            pageIds = self.tuneInterface.getSelectedIds()

        if instruments == False:
            instruments = []
            for inst in self.trackInstrument:
                instruments.append(inst.instrumentId)

        self.noteDB.deletePages(pageIds[:], instruments)

    def pageDuplicate(self, after = -1, pageIds = False):

        if after == -1: after = self.tuneInterface.getLastSelected()
        if not pageIds: pageIds = self.tuneInterface.getSelectedIds()

        new = self.noteDB.duplicatePages(pageIds[:], after)
        self.displayPage(new[self.displayedPage])
        self.tuneInterface.selectPages(new.values())

    def pageAdd(self, after = -1, beats = False, color = False, instruments = False):

        if after == -1: after = self.tuneInterface.getLastSelected()
        page = self.noteDB.getPage(self.displayedPage)
        if not beats: beats = page.beats
        if not color: color = page.color
        if not instruments: instruments = page.instruments

        # TODO think about network mode here...
        self.displayPage(self.noteDB.addPage(-1, NoteDB.Page(beats,color,instruments), after))

    def pageBeats(self, pageIds = -1):

        if pageIds == -1: pageIds = self.tuneInterface.getSelectedIds()

        # TODO change the beats

    #=======================================================
    # NoteDB notifications

    def notifyPageAdd(self, id, at):
        return

    def notifyPageDelete(self, which, safe):
        if self.displayedPage in which:
            self.displayPage( safe )

    def notifyPageDuplicate(self, new, at):
        return

    def notifyPageMove(self, which, low, high):
        return

    def notifyPageUpdate(self, page, parameter, value):
        pass

    def notifyNoteAdd(self, page, track, id):
        if (Config.DEBUG > 3) : print 'INFO: adding note to loop', page, track, id
        n = self.noteDB.getNote(page, track, id)
        self.csnd.loopPlay(n,0)
        if self.playing and (n.page in self.page_onset ):
            onset = n.cs.onset + self.page_onset[n.page]
            self.csnd.loopUpdate(n, NoteDB.PARAMETER.ONSET, onset, 1)  #set onset + activate

    def notifyNoteDelete(self, page, track, id):
        if (Config.DEBUG > 3) : print 'INFO: deleting note from loop', page, track, id
        self.csnd.loopDelete1(page,id)
    def notifyNoteUpdate(self, page, track, id, parameter, value):
        if (Config.DEBUG > 3) : print 'INFO: updating note ', page, id, parameter, value
        note = self.noteDB.getNote(page, track, id)
        self.csnd.loopUpdate(note, parameter, value, -1)

    #-----------------------------------
    # load and save functions
    #-----------------------------------

    def waitToSet(self):
        self.csnd.setMasterVolume(self._data['volume'])
        self.csnd.setTempo(self._data['tempo'])
        self.initTrackVolume()

    def handleSave(self, widget = None):

        chooser = Gtk.FileChooserDialog(
                title='Save Tune',
                action=Gtk.FileChooserAction.SAVE,
                buttons=(Gtk.STOCK_CANCEL,Gtk.ResponeType.CANCEL,Gtk.STOCK_SAVE,Gtk.ResponseType.OK))
        filter = Gtk.FileFilter()
        filter.add_pattern('*.tam')
        chooser.set_filter(filter)
        chooser.set_current_folder(Config.DATA_DIR)

        for f in chooser.list_shortcut_folder_uris():
            chooser.remove_shortcut_folder_uri(f)

        if chooser.run() == Gtk.ResponseType.OK:
            ofilename = chooser.get_filename()
            if ofilename[-4:] != '.tam':
                ofilename += '.tam'
            try:
                ofile = open(ofilename, 'w')
                ofilestream = ControlStream.TamTamOStream (ofile)
                self.noteDB.dumpToStream(ofilestream)
                ofilestream.track_vol(self._data['track_volume'])
                ofilestream.master_vol(self._data['volume'])
                ofilestream.tempo(self._data['tempo'])
                ofile.close()
            except OSError,e:
                print 'ERROR: failed to open file %s for writing\n' % ofilename
        chooser.destroy()

    def handleLoopSave(self):
        date = str(time.localtime()[3]) + '-' + str(time.localtime()[4]) + '-' + str(time.localtime()[5])
        ofilename = Config.DATA_DIR + '/' + date + '.ttl'
        ofile = open(ofilename, 'w')
        ofilestream = ControlStream.TamTamOStream (ofile)
        self.noteDB.dumpToStream(ofilestream)
        ofilestream.track_vol(self._data['track_volume'])
        ofilestream.master_vol(self._data['volume'])
        ofilestream.tempo(self._data['tempo'])
        ofile.close()

    def handleJournalSave(self, file_path):
        ofile = open(file_path, 'w')
        ofilestream = ControlStream.TamTamOStream (ofile)
        self.noteDB.dumpToStream(ofilestream)
        ofilestream.track_vol(self._data['track_volume'])
        ofilestream.master_vol(self._data['volume'])
        ofilestream.tempo(self._data['tempo'])
        ofile.close()

    def _loadFile( self, path ):
        try:
            oldPages = self.noteDB.getTune()[:]

            ifile = open(path, 'r')
            ttt = ControlStream.TamTamTable ( self.noteDB )
            ttt.parseFile(ifile)
            self.trackInstrument = self.trackInstrumentDefault[:] # these will get set correctly in displayPage
            self._data['track_volume'] = ttt.tracks_volume
            self._data['volume'] = float(ttt.masterVolume)
            self._data['tempo'] = float(ttt.tempo)
            #self.GUI["2volumeAdjustment"].set_value(self._data['volume'])
            #self.GUI["2tempoAdjustment"].set_value(self._data['tempo'])
            ifile.close()

            self.noteDB.deletePages( oldPages )

            self.tuneInterface.selectPages( self.noteDB.getTune() )
        except OSError,e:
            print 'ERROR: failed to open file %s for reading\n' % ofilename

    def handleLoad(self, widget):
        chooser = Gtk.FileChooserDialog(
                title='Load Tune',
                action=Gtk.FileChooserAction.OPEN,
                buttons=(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK))

        filter = Gtk.FileFilter()
        filter.add_pattern('*.tam')
        chooser.set_filter(filter)
        chooser.set_current_folder(Config.DATA_DIR)

        for f in chooser.list_shortcut_folder_uris():
            chooser.remove_shortcut_folder_uri(f)

        if chooser.run() == Gtk.ResponseType.OK:
            print 'DEBUG: loading file: ', chooser.get_filename()
            self._loadFile( chooser.get_filename() )

        chooser.destroy()
        self.delay = GObject.timeout_add(1000, self.waitToSet)

    def handleJournalLoad(self,file_path):
        self.journalCalled = True
        self._loadFile( file_path )

    #-----------------------------------
    # Record functions
    #-----------------------------------
    def handleMicRecord(self, widget, data):
        self.csnd.micRecording(data)
    def handleCloseMicRecordWindow(self, widget = None, data = None):
        self.micRecordWindow.destroy()
        self.micRecordButton.set_active(False)

    #-----------------------------------
    # callback functions
    #-----------------------------------
    def handleKeyboardShortcuts(self,event):
        keyval = event.keyval

        if not Config.HAVE_TOOLBOX:
            # TODO process for Config.HAVE_TOOLBOX as well
            if self.activity.activity_toolbar.title.is_focus():
                return

        # backspace and del keys
        if keyval == Gdk.KEY_Delete or keyval == Gdk.KEY_BackSpace:
            if self.context == CONTEXT.PAGE: self.pageDelete()
            if self.context == CONTEXT.TRACK: self.trackDelete()
            if self.context == CONTEXT.NOTE: self.noteDelete()
        # plus key
        if keyval == Gdk.KEY_Equal:
            self.pageAdd()
        # duplicate ctrl-c
        if event.state == Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_C:
            if self.context == CONTEXT.PAGE: self.pageDuplicate()
            if self.context == CONTEXT.TRACK: self.trackDuplicate()
            if self.context == CONTEXT.NOTE: self.noteDuplicate()
        #Arrows
        if event.state == Gdk.ModifierType.SHIFT_MASK:
            # up/down arrows volume
            if keyval == Gdk.KEY_Up: self.trackInterface.noteStepVolume(0.1)
            if keyval == Gdk.KEY_Down: self.trackInterface.noteStepVolume(-0.1)
            # left/right arrows onset
            if keyval == Gdk.KEY_Left: self.trackInterface.noteStepDuration(-1)
            if keyval == Gdk.KEY_Right: self.trackInterface.noteStepDuration(1)
        else:
            # up/down arrows pitch
            if keyval == Gdk.KEY_Up: self.trackInterface.noteStepPitch(1)
            if keyval == Gdk.KEY_Down: self.trackInterface.noteStepPitch(-1)
            # left/right arrows duration
            if keyval == Gdk.KEY_Left: self.trackInterface.noteStepOnset(-1)
            if keyval == Gdk.KEY_Right: self.trackInterface.noteStepOnset(1)
        #Save Loop
        if event.state == Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_S:
            self.handleLoopSave()


    def onKeyPress(self,widget,event):

        self.handleKeyboardShortcuts(event)
        Config.ModKeys.keyPress(event.hardware_keycode)
        key = event.hardware_keycode

        # If the key is already in the dictionnary, exit function (to avoir key repeats)
        if self.kb_keydict.has_key(key):
                return

        # Assign on which track the note will be created according to the number of keys pressed
        if self.trackCount >= 9:
            self.trackCount = 6
        fakeTrack = self.trackCount
        self.trackCount += 1

        # If the pressed key is in the keymap
        if KEY_MAP_PIANO.has_key(key):
            pitch = KEY_MAP_PIANO[key]
            duration = -1

            # get instrument from top selected track if a track is selected
            if True in self.trackSelected:
                index = self.trackSelected.index(True)
                instrument = self.getTrackInstrument(index).name
            else:
                return

            tid = index

            # pitch, inst and duration for drum recording
            if tid == Config.NUMBER_OF_TRACKS-1:
                if GenerationConstants.DRUMPITCH.has_key( pitch ):
                    pitch = GenerationConstants.DRUMPITCH[pitch]
                if self.instrumentDB.instNamed[instrument].kit != None:
                    instrument = self.instrumentDB.instNamed[instrument].kit[pitch].name
                duration = 100

            # Create and play the note
            self.kb_keydict[key] = CSoundNote(onset = 0,
                                        pitch = pitch,
                                        amplitude = 1,
                                        pan = 0.5,
                                        duration = duration,
                                        trackId = fakeTrack,
                                        instrumentId = self.instrumentDB.instNamed[instrument].instrumentId,
                                        tied = False,
                                        mode = 'edit')
            self.csnd.play(self.kb_keydict[key], 0.3)

            # doesn't keep track of keys for drum recording
            if tid == Config.NUMBER_OF_TRACKS-1:
                del self.kb_keydict[key]

            # remove previosly holded key from dictionary
            if len(self.kb_keydict) > 1:
                for k in self.kb_keydict.keys():
                    if k != key:
                        GObject.source_remove( self.durUpdate )
                        self.durUpdate = False
                        self.kb_keydict[k].duration = 0.5
                        self.kb_keydict[k].amplitude = 0
                        self.kb_keydict[k].decay = 0.7
                        self.kb_keydict[k].tied = False
                        self.csnd.play(self.kb_keydict[k], 0.3)
                        if not self.kb_record:
                            del self.kb_keydict[k]
                            return
                        self.removeRecNote(self.csId)

            if not self.kb_record:
                return

            #record the note on track
            pageList = self.tuneInterface.getSelectedIds()
            pid = self.displayedPage
            minOnset = self.page_onset[pid]
            onsetQuantized = Config.DEFAULT_GRID * int((self.csnd.loopGetTick() - minOnset) / Config.DEFAULT_GRID + 0.5)

            maxOnset = self.noteDB.getPage(pid).ticks
            if onsetQuantized >= maxOnset:
                if pid == pageList[-1]:
                    pid = pageList[0]
                else:
                    if len(pageList) > 1:
                        pidPos = pageList.index(pid)
                        pid = pageList[pidPos+1]
                onsetQuantized = 0

            if tid < Config.NUMBER_OF_TRACKS-1:
                for n in self.noteDB.getNotesByTrack( pid, tid ):
                    if onsetQuantized < n.cs.onset:
                        break
                    if onsetQuantized >= n.cs.onset + n.cs.duration:
                        continue
                    if onsetQuantized < n.cs.onset + n.cs.duration - 2:
                        self.noteDB.deleteNote(n.page, n.track, n.id)
                    elif onsetQuantized - n.cs.onset < 1:
                        self.noteDB.deleteNote(n.page, n.track, n.id)
                    else:
                        self.noteDB.updateNote( n.page, n.track, n.id, PARAMETER.DURATION, onsetQuantized - n.cs.onset )
                    break
            else:
                for n in self.noteDB.getNotesByTrack( pid, tid ):
                    if onsetQuantized < n.cs.onset:
                        break
                    if onsetQuantized == n.cs.onset:
                        if pitch < n.cs.pitch:
                            break
                        if pitch == n.cs.pitch:
                            return # don't bother with a new note

            csnote = CSoundNote(onset = 0,
                                        pitch = pitch,
                                        amplitude = 1,
                                        pan = 0.5,
                                        duration = duration,
                                        trackId = index,
                                        instrumentId = self.instrumentDB.instNamed[instrument].instrumentId,
                                        tied = False,
                                        mode = 'edit')

            csnote.onset = onsetQuantized
            csnote.duration = 1
            csnote.pageId = pid
            id = self.noteDB.addNote(-1, pid, tid, csnote)
            # csId: PageId, TrackId, Onset, Key, DurationSetOnce
            self.csId = [pid, tid, id, csnote.onset, key, False ]
            if tid < Config.NUMBER_OF_TRACKS-1:
                self.durUpdate = GObject.timeout_add( 25, self.durationUpdate )

    def onKeyRelease(self,widget,event):

        Config.ModKeys.keyRelease(event.hardware_keycode)
        key = event.hardware_keycode

        if True in self.trackSelected:
            index = self.trackSelected.index(True)
            if index == Config.NUMBER_OF_TRACKS-1:
                return
        else:
            return

        if KEY_MAP_PIANO.has_key(key) and self.kb_keydict.has_key(key):
            if self.kb_record and self.durUpdate:
                GObject.source_remove( self.durUpdate )
                self.durUpdate = False

            if self.instrumentDB.instId[ self.kb_keydict[key].instrumentId ].csoundInstrumentId == Config.INST_TIED:
                self.kb_keydict[key].duration = 0.5
                self.kb_keydict[key].amplitude = 0
                self.kb_keydict[key].decay = 0.5
                self.kb_keydict[key].tied = False
                self.csnd.play(self.kb_keydict[key], 0.3)
            if not self.kb_record:
                del self.kb_keydict[key]
                return

            self.removeRecNote(self.csId)

    def removeRecNote(self, csId):
        newDuration = (int(self.csnd.loopGetTick()) - self.page_onset[csId[0]]) - csId[3]
        maxTick = self.noteDB.getPage(csId[0]).ticks

        if not csId[5]:  # handle notes that were created right at the end of a page
            if newDuration > maxTick//2:
                newDuration = 1
            else:
                csId[5] = True

        if newDuration < -Config.DEFAULT_GRID_DIV2:  # we looped around
            newDuration = maxTick - self.csId[3]
        elif newDuration < 1:
            newDuration = 1

        if (csId[3] + newDuration) > maxTick:
            newDuration = maxTick - csId[3]

        for n in self.noteDB.getNotesByTrack(csId[0], csId[1]):
            if n.id == csId[2]:
                continue
            if csId[3] + newDuration <= n.cs.onset:
                break
            if csId[3] >= n.cs.onset + n.cs.duration:
                continue
            self.noteDB.deleteNote(n.page, n.track, n.id)
            break

        self.noteDB.updateNote(csId[0], csId[1], csId[2], PARAMETER.DURATION, newDuration)

        del self.kb_keydict[csId[4]]

    def durationUpdate(self):
        newDuration = (int(self.csnd.loopGetTick()) - self.page_onset[self.csId[0]]) - self.csId[3]

        maxTick = self.noteDB.getPage(self.csId[0]).ticks
        stop = False

        if not self.csId[5]:  # handle notes that were created right at the end of a page
            if newDuration > maxTick//2:
                newDuration = 1
            else:
                self.csId[5] = True

        if newDuration < -Config.DEFAULT_GRID_DIV2:  # we looped around
            newDuration = maxTick - self.csId[3]
            stop = True
        elif newDuration < 1:
            newDuration = 1

        if (self.csId[3] + newDuration) > maxTick:
            stop = True
            newDuration = maxTick - self.csId[3]

        for n in self.noteDB.getNotesByTrack(self.csId[0], self.csId[1]):
            if n.id == self.csId[2]:
                continue
            if self.csId[3] + newDuration <= n.cs.onset:
                break
            if self.csId[3] >= n.cs.onset + n.cs.duration:
                continue
            self.noteDB.deleteNote(n.page, n.track, n.id)
            break

        self.noteDB.updateNote(self.csId[0], self.csId[1], self.csId[2], PARAMETER.DURATION, newDuration)

        if stop:
            key = self.csId[4]
            if self.instrumentDB.instId[ self.kb_keydict[key].instrumentId ].csoundInstrumentId == Config.INST_TIED:
                self.kb_keydict[key].duration = 0.5
                self.kb_keydict[key].amplitude = 0
                self.kb_keydict[key].decay = 0.5
                self.kb_keydict[key].tied = False
                self.csnd.play(self.kb_keydict[key], 0.3)

            del self.kb_keydict[key]
            return False
        return True

    def delete_event(self, widget, event, data = None):
        return False

    def onDestroy(self):

        if (Config.DEBUG > 1): print TP.PrintAll()

    def setContextState(self, context, state):
        if context == CONTEXT.TRACK:
            self.contextTrackActive = state
            if not state:
                if self.context == CONTEXT.TRACK:
                    if self.contextNoteActive:
                        self.setContext(CONTEXT.NOTE)
                    else:
                        self.setContext(CONTEXT.PAGE)
        else:
            self.contextNoteActive = state
            if not state:
                if self.context == CONTEXT.NOTE:
                    self.prevContext()

    def setContext(self, context, force = False):

        if self.context == context and not force: return

        self.context = context

        #if self.context == CONTEXT.NOTE:
        #    self._generateToolbar.generationButton.set_sensitive(False)
        #else:
        #    self._generateToolbar.generationButton.set_sensitive(True)

    def getContext(self):
        return self.context

    def prevContext(self):
        if self.context == CONTEXT.TRACK:
            self.setContext(CONTEXT.PAGE)
        elif self.contextTrackActive:
            self.setContext(CONTEXT.TRACK)
        else:
            self.setContext(CONTEXT.PAGE)

    def nextContext(self):
        if self.context == CONTEXT.TRACK:
            self.setContext(CONTEXT.NOTE)
        elif self.contextTrackActive:
            self.setContext(CONTEXT.TRACK)
        else:
            self.setContext( CONTEXT.NOTE )

    #-----------------------------------
    # access functions (not sure if this is the best way to go about doing this)
    #-----------------------------------
    def getVolume(self):
        return self._data["volume"]

    def getTempo(self):
        return self._data["tempo"]
        #return round( self.tempoAdjustment.value, 0 )

    def getBeatsPerPage(self):
        return int(round(self.beatsPerPageAdjustment.value, 0 ))

    def getWindowTitle(self):
        return "Tam-Tam [Volume %i, Tempo %i, Beats/Page %i]" % (self.getVolume(), self.getTempo(), self.getBeatsPerPage())


class InstrumentButton(Gtk.DrawingArea):

    def __init__(self, owner, index, backgroundFill):
        Gtk.DrawingArea.__init__(self)

        self.index = index
        self.owner = owner

        self.color = { "background":   Gdk.Color.parse(backgroundFill)[1],
                       "divider":      Gdk.Color.parse("#000")[1],
                       "+/-":          Gdk.Color.parse('#818286')[1],
                       "+/-Highlight": Gdk.Color.parse("#FFF")[1] }

        self.surface = None
        self.primary = None
        self.primaryWidth = self.primaryHeight = 1
        self.secondary = None
        self.secondaryWidth = self.secondaryHeight = 1

        self.clicked = None
        self.hover = None

        self.add_events( Gdk.EventMask.BUTTON_PRESS_MASK
                       | Gdk.EventMask.BUTTON_RELEASE_MASK
                       | Gdk.EventMask.POINTER_MOTION_MASK
                       | Gdk.EventMask.POINTER_MOTION_HINT_MASK
                       | Gdk.EventMask.LEAVE_NOTIFY_MASK
                       | Gdk.EventMask.ENTER_NOTIFY_MASK )
        self.connect( "size-allocate", self.size_allocate )
        self.connect( "button-press-event", self.button_press )
        self.connect( "button-release-event", self.button_release )
        self.connect( "motion-notify-event", self.motion_notify )
        self.connect( "leave-notify-event", self.leave_notify )
        self.connect( "draw", self.expose )

    def size_allocate(self, widget, allocation):
        self.alloc = allocation
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, allocation.width, allocation.height)
        self.primaryX = (self.alloc.width - self.primaryWidth) // 2
        self.primaryY = (self.alloc.height - self.primaryHeight) // 2
        self.secondaryX = (self.alloc.width - self.secondaryWidth) // 2
        self.secondaryY = self.alloc.height//2

        self.hotspots = [ [ self.alloc.width-24, self.alloc.height-29, self.alloc.width-8, self.alloc.height-13 ],
                          [ self.alloc.width-24, self.alloc.height//2-23, self.alloc.width-8, self.alloc.height//2-7 ] ]

        self.hotspots[0] += [ (self.hotspots[0][0]+self.hotspots[0][2])//2, (self.hotspots[0][1]+self.hotspots[0][3])//2 ]
        self.hotspots[1] += [ (self.hotspots[1][0]+self.hotspots[1][2])//2, (self.hotspots[1][1]+self.hotspots[1][3])//2 ]

        self._updatePixmap()

    def button_press(self, widget, event):
        self.clicked = "PRIMARY"
        self.hover = None
        x, y = widget.get_pointer()

        if     x >= self.hotspots[0][0] and x <= self.hotspots[0][2] \
           and y >= self.hotspots[0][1] and y <= self.hotspots[0][3]:
            self.clicked = "HOTSPOT_0"

        elif self.secondary != None:

            if     x >= self.hotspots[1][0] and x <= self.hotspots[1][2] \
               and y >= self.hotspots[1][1] and y <= self.hotspots[1][3]:
                self.clicked = "HOTSPOT_1"

            elif y > self.alloc.height//2:
                self.clicked = "SECONDARY"

    def button_release(self, widget, event):
        if self.clicked == "PRIMARY":
            self.owner.pickInstrument(self, self.index, True)
        elif self.clicked == "SECONDARY":
            self.owner.pickInstrument(self, self.index, False)
        elif self.clicked == "HOTSPOT_0":
            if self.secondary != None:  # remove secondary
                self.owner.clearInstrument(self.index, False)
            else:  # add secondary
                self.owner.pickInstrument(self, self.index, False)
        else: # HOTSPOT_1, remove primary
            self.owner.clearInstrument(self.index, True)

        self.clicked = None

    def motion_notify(self, widget, event):

        if self.clicked != None:
            return

        x, y = event.x, event.y
        #if event.is_hint:
        #    x, y, state = widget.window.get_pointer()
        #    event.x = float(x)
        #    event.y = float(y)
        #    event.state = state

        if     x >= self.hotspots[0][0] and x <= self.hotspots[0][2] \
           and y >= self.hotspots[0][1] and y <= self.hotspots[0][3]:
            if self.hover != "HOTSPOT_0":
                self.hover = "HOTSPOT_0"
                self.queue_draw()


        elif    self.secondary != None \
           and x >= self.hotspots[1][0] and x <= self.hotspots[1][2] \
           and y >= self.hotspots[1][1] and y <= self.hotspots[1][3]:
            if self.hover != "HOTSPOT_1":
                self.hover = "HOTSPOT_1"
                self.queue_draw()
        else:
            if self.hover != None:
                self.hover = None
                self.queue_draw()

    def leave_notify( self, widget, event ):
        if event.mode != Gdk.CrossingMode.NORMAL:
            return
        if self.hover != None:
            self.hover = None
            if self.clicked == None:
                self.queue_draw()


    def setPrimary(self, img):
        # img is a cairo.ImageSurface
        self.primary = img
        self.primaryWidth = img.get_width()
        self.primaryHeight = img.get_height()
        if self.surface:
            self.primaryX = (self.alloc.width - self.primaryWidth) // 2
            self.primaryY = (self.alloc.height - self.primaryHeight) // 2
            self._updatePixmap()

    def setSecondary(self, img):
        self.secondary = img
        if img != None:
            self.secondaryWidth = img.get_width()
            self.secondaryHeight = img.get_height()
            self.secondaryOffset = self.secondaryHeight//2
            if self.surface:
                self.secondaryX = (self.alloc.width - self.secondaryWidth) // 2
                self.secondaryY = self.alloc.height//2
        if self.surface:
            self._updatePixmap()

    def _updatePixmap(self):
        cxt = cairo.Context(self.surface)
        cxt.set_source_rgb(*gdk_color_to_cairo(self.color["background"]))
        cxt.rectangle(0, 0, self.alloc.width, self.alloc.height)
        cxt.fill()
        if self.secondary != None:
            cxt.set_source_surface(self.primary, 0, 0)
            cxt.set_source_surface(self.secondary, 0, self.secondaryOffset)
            cxt.paint()
            cxt.set_source_rgb(*gdk_color_to_cairo(self.color["divider"]))
            cxt.move_to(2, self.alloc.height//2)
            cxt.line_to(self.alloc.width-4, self.alloc.height//2)
            cxt.stroke()
        else:
            cxt.set_source_surface(self.primary, 0, 0)
            cxt.paint()
        self.queue_draw()

    def expose(self, widget, cr):
        cr.set_source_surface(self.surface, 0, 0)
        cr.paint()
        cr.set_line_width(4)
        if self.secondary != None:
            if self.clicked == "HOTSPOT_0" or (self.clicked == None and self.hover == "HOTSPOT_0" ):
                cr.set_source_rgb(*gdk_color_to_cairo(self.color["+/-Highlight"]))
            else:
                cr.set_source_rgb(*gdk_color_to_cairo(self.color["+/-"]))
            cr.move_to(self.hotspots[0][0], self.hotspots[0][5])
            cr.line_to(self.hotspots[0][2], self.hotspots[0][5])
            if self.clicked == "HOTSPOT_1" or (self.clicked == None and self.hover == "HOTSPOT_1" ):
                cr.set_source_rgb(*gdk_color_to_cairo(self.color["+/-Highlight"]))
            else:
                cr.set_source_rgb(*gdk_color_to_cairo(self.color["+/-"]))
            cr.move_to(self.hotspots[1][0], self.hotspots[1][5])
            cr.line_to(self.hotspots[1][2], self.hotspots[1][5])
        else:
            if self.clicked == "HOTSPOT_0" or self.hover == "HOTSPOT_0":
                cr.set_source_rgb(*gdk_color_to_cairo(self.color["+/-Highlight"]))
            else:
                cr.set_source_rgb(*gdk_color_to_cairo(self.color["+/-"]))
            cr.move_to(self.hotspots[0][0], self.hotspots[0][5])
            cr.line_to(self.hotspots[0][2], self.hotspots[0][5])
            cr.move_to(self.hotspots[0][4], self.hotspots[0][1])
            cr.line_to(self.hotspots[0][4], self.hotspots[0][3])
        cr.stroke()

    def set_palette(self, palette):
        pass


class NoneInvoker(Invoker):

    def __init__(self):
        Invoker.__init__(self)
        self._position_hint = Invoker.AT_CURSOR

    def get_rect(self):
        return Gdk.Rectangle()

    def get_toplevel(self):
        return None

class Popup(Palette):

    def __init__(self, label, owner):
        Palette.__init__(self, label)

        self.owner = owner

        self.block = None

        self.props.invoker = NoneInvoker()
        self.set_group_id( "TamTamPopup" )

        self.connect( "activate", self.on_key_press )
        self.connect( "activate", self.on_key_release )

        #self.connect( "focus_out_event", self.closePopup )

    def destroy(self):
        pass

    def _leave_notify_event_cb(self, widget, event):
        return  # don't popdown()

    def _show(self):
        Palette._show(self)

        if self._palette_popup_sid != None:
            self._palette_popup_sid = None

    def popup(self, immediate = False):
        if hasattr(self, '_set_state'):
            self._set_state(self.SECONDARY)
            Palette.popup(self, immediate)
        else:
            Palette.popup(self, immediate, state = Palette.SECONDARY)

    def popdown(self, immediate = False):
        self.block = None

        Palette.popdown(self, immediate)

    def updatePosition(self):
        self.props.invoker._cursor_x = -1
        self.props.invoker._cursor_y = -1
        self._update_position()

    def closePopup(self, widget, event):
        self.popdown( True )

    def on_key_press(self, widget, event):
        self.owner.onKeyPress(widget, event)

    def on_key_release(self, widget, event):
        self.owner.onKeyRelease(widget, event)

class instrumentPalette(Popup):
    ICON_SIZE = (70,70)
    def __init__(self, label, edit):
        Popup.__init__(self, label, edit)

        self.instrumentDB = InstrumentDB.getRef()
        self.edit = edit

        self.skip = False
        self.skipVolAdj = False
        self.lastClickedTrack = None

        self.mainBox = Gtk.VBox()
        self.volumeBox = Gtk.HBox()
        self.instrumentMainBox = Gtk.HBox()


        self.muteButtonLabel = Gtk.Label(_('M'))
        self.muteButton = Gtk.CheckButton()
        self.muteButton.connect("toggled",self.handlemuteButton)
        self.muteButton.set_active(True)
        self.muteButton.set_tooltip_text(_('Mute track'))
        self.soloButtonLabel = Gtk.Label(_('S'))
        self.soloButton = Gtk.CheckButton()
        self.soloButton.connect("toggled",self.handlesoloButton)
        self.soloButton.set_active(True)
        self.soloButton.set_tooltip_text(_('Solo track'))

        self.volumeSliderAdj = Gtk.Adjustment( self.edit._data["track_volume"][0], 0, 100, 1, 1, 0 )
        self.volumeSliderAdj.connect( "value-changed", self.handleTrackVolume)
        self.volumeSlider =  Gtk.HScale(adjustment = self.volumeSliderAdj)
        self.volumeSlider.set_size_request(250, -1)
        self.volumeSlider.set_inverted(False)
        self.volumeSlider.set_draw_value(False)

        self.categories = Config.CATEGORIES
        self.categoryBox = BigComboBox()
        for category in self.categories:
            image = imagefile(category.lower() + '.png')
            if not os.path.isfile(image):
                image = imagefile('generic.png')
            #self.categoryBox.append_item(category, category.capitalize(),
            #        icon_name = image, size = instrumentPalette.ICON_SIZE)
        self.categoryBox.connect('changed', self.handleCategoryChange)

        self.icons = []

        for i in self.instrumentDB.inst:
            if not i.kit and not i.kitStage:
                self.icons.append([i, GdkPixbuf.Pixbuf.new_from_file_at_size(
                    i.img, instrumentPalette.ICON_SIZE[0],
                    instrumentPalette.ICON_SIZE[1])])

        self.instruments = []
        self.instrumentBox1 = BigComboBox()
        self.instrumentBox1.connect('changed', self.handleInstrumentChange)

        self.volumeBox.pack_start(self.muteButtonLabel, expand=True, fill=True, padding = 5)
        self.volumeBox.pack_start(self.muteButton, expand=True, fill=True, padding = 5)
        #self.volumeBox.pack_start(self.soloButtonLabel, padding = 5)
        #self.volumeBox.pack_start(self.soloButton, padding = 5)
        self.volumeBox.pack_start(self.volumeSlider, expand=True, fill=True, padding=5)
        self.mainBox.pack_start(self.volumeBox, expand=True, fill=True, padding=5)
        self.instrumentMainBox.pack_start(self.categoryBox, expand=True, fill=True, padding=5)
        self.instrumentMainBox.pack_start(self.instrumentBox1, expand=True, fill=True, padding=5)
        self.mainBox.pack_start(self.instrumentMainBox, expand=True, fill=True, padding=5)
        self.mainBox.show_all()

        self.set_content(self.mainBox)

    def handleTrackVolume(self, widget):
        if not self.skipVolAdj:
            if self.lastClickedTrack != None:
                self.edit.handleTrackVolume(widget = widget, track = self.lastClickedTrack)

    def handlemuteButton(self, widget):
        if not self.skipVolAdj:
            if self.lastClickedTrack != None:
                self.edit.handlemuteButton(widget, self.lastClickedTrack)

    def handlesoloButton(self, widget, event = None):
        pass

    def handleInstrumentChange(self, widget):
        if not self.skip and self.instrumentBox1.get_active() != -1:
            instrument = widget.props.value
            self.edit.donePickInstrument(instrument)
            time.sleep(0.05)
            self.edit.playInstrumentNote(instrument)
            self.popdown(True)

    def handleCategoryChange(self, widget):
        category = widget.props.value.lower()

        self.instrumentBox1.set_active(-1)
        self.instrumentBox1.remove_all()
        self.instruments = []

        for i in self.icons:
            if category == 'all' or i[0].category == category:
                #self.instrumentBox1.append_item(i[0].name, None, pixbuf = i[1])
                self.instruments.append(i[0].name)

        if not self.skip:
            self.instrumentBox1.popup()

    def setInstrument(self, instrument):
        self.skip = True
        self.categoryBox.set_active(self.categories.index(instrument.category))
        self.instrumentBox1.set_active(self.instruments.index(instrument.name))
        self.skip = False

    def setBlock( self, widget = None, event = None, block = None ):
        if self.is_up():
            self.popdown(True)
        else:
            self.set_primary_text(_('Track %s Properties' % str(block+1)))
            self.skipVolAdj = True
            self.volumeSliderAdj.set_value(self.edit._data["track_volume"][block])
            if self.edit.trackActive[block]:
                self.muteButton.set_active(True)
            else:
                self.muteButton.set_active(False)
            self.skipVolAdj = False
            self.lastClickedTrack = block
            self.popup( True )

class drumPalette(Popup):
    ICON_SIZE = (70,70)
    def __init__(self, label, edit, trackID):
        Popup.__init__(self, label, edit)

        self.instrumentDB = InstrumentDB.getRef()
        self.trackID = trackID
        self.edit = edit

        self.skip = False


        self.mainBox = Gtk.VBox()
        self.volumeBox = Gtk.HBox()
        self.instrumentMainBox = Gtk.HBox()

        self.muteButton = Gtk.CheckButton()
        self.muteButton.connect("toggled",self.edit.handlemuteButton, self.trackID)
        self.muteButton.connect("button-press-event",self.edit.handlemuteButtonRightClick, self.trackID)
        self.muteButton.set_active(True)
        self.muteButton.set_tooltip_text( _('Left click to mute, right click to solo'))

        if self.trackID < 4:
            exec "self.volumeSliderAdj = self.edit.GUI['2instrument%svolumeAdjustment']" % str(self.trackID+1)
        else:
            self.volumeSliderAdj = self.edit.GUI["2drumvolumeAdjustment"]
        self.volumeSliderAdj.connect( "value-changed", self.edit.handleTrackVolume, self.trackID)
        self.volumeSlider =  Gtk.HScale(adjustment = self.volumeSliderAdj)
        self.volumeSlider.set_size_request(250, -1)
        self.volumeSlider.set_inverted(False)
        self.volumeSlider.set_draw_value(False)

        self.drums = self.getDrums()

        self.drumBox = BigComboBox()
        self.loadDrumMenu(self.getDrums())
        self.drumBox.connect('changed', self.handleInstrumentChange)

        self.volumeBox.pack_start(self.muteButton, expand=True, fill=True, padding = 5)
        self.volumeBox.pack_start(self.volumeSlider, expand=True, fill=True, padding = 5)
        self.mainBox.pack_start(self.volumeBox, expand=True, fill=True, padding = 5)
        self.instrumentMainBox.pack_start(self.drumBox, False, False, padding = 5)
        self.mainBox.pack_start(self.instrumentMainBox, expand=True, fill=True, padding = 5)
        self.mainBox.show_all()

        self.set_content(self.mainBox)

    def handleInstrumentChange(self, widget):
        if not self.skip:
            drum = widget.props.value
            self.edit.donePickDrum(drum)
            time.sleep(0.05)
            self.edit.playInstrumentNote(drum)
            self.popdown(True)

    def setDrum(self, Drum):
        self.skip = True
        self.drumBox.set_active(self.drums.index(Drum))
        self.skip = False

    def loadDrumMenu(self, instruments):
        self.drumBox.clear()
        for instrument in instruments:
            image = imagefile(instrument + '.png')
            if not os.path.isfile(image):
                image = imagefile('generic.png')
            #self.drumBox.append_item(instrument, text = None, icon_name = image, size = instrumentPalette.ICON_SIZE)

    def getDrums(self):
        return sorted([instrument for instrument in self.instrumentDB.instNamed.keys() if self.instrumentDB.instNamed[instrument].kit])

    def setBlock( self, widget = None, event = None, block = None ):
        if self.is_up():
            self.popdown(True)
        else:
            self.popup( True )
