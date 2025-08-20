from gi.repository import Gtk
from gi.repository import Gdk

import common.Config as Config

from gettext import gettext as _
from sugar3.graphics import style
from sugar3.graphics.palette import Palette, Invoker
from gi.repository import GObject

from Jam import Block
from common.Util.NoteDB import PARAMETER
from common.Util.CSoundNote import CSoundNote
from common.Util.CSoundClient import new_csound_client
from Jam.Parasite import LoopParasite

from common.Generation.Generator import generator1, GenerationParameters
from common.Generation.GenerationConstants import GenerationConstants

class SELECTNOTES:
    ALL = -1
    NONE = 0
    ADD = 1
    REMOVE = 2
    FLIP = 3
    EXCLUSIVE = 4

class NoneInvoker( Invoker ):

    def __init__( self ):
        Invoker.__init__( self )
        self._position_hint = Invoker.AT_CURSOR

    def get_rect( self ):
        return ( 0, 0, 0, 0 )

    def get_toplevel( self ):
        return None

class Popup( Palette ):

    def __init__( self, label, owner ):
        Palette.__init__( self, label )

        self.owner = owner

        self.block = None

        self.props.invoker = NoneInvoker()
        self.set_group_id( "TamTamPopup" )

        # TODO: is needed now?
        #self.connect( "key-press-event", self.on_key_press )
        #self.connect( "key-release-event", self.on_key_release )

        #self.connect( "focus_out_event", self.closePopup )

    def destroy( self ):
        pass

    def _leave_notify_event_cb( self, widget, event ):
        return # don't popdown()

    def _show( self ):
        Palette._show( self )

        if self._palette_popup_sid != None:
            self._palette_popup_sid = None

    def popup( self, immediate = False ):
        if hasattr(self, '_set_state'):
            self._set_state(self.SECONDARY)
            Palette.popup( self, immediate)
        else:
            Palette.popup( self, immediate, state = Palette.SECONDARY )

    def popdown( self, immediate = False ):
        self.block = None

        Palette.popdown( self, immediate )

    def updatePosition( self ):
        self.props.invoker._cursor_x = -1
        self.props.invoker._cursor_y = -1
        self._update_position()

#    def closePopup( self, widget, event ):
#        self.popdown( True )

#    def on_key_press( self, widget, event ):
#        self.owner.onKeyPress( widget, event )

#    def on_key_release( self, widget, event ):
#        self.owner.onKeyRelease( widget, event )

    def setBlock( self, block ):
        if self.is_up():
            self.updatePosition()
        else:
            self.popup( True )


class Instrument( Popup ):

    def __init__( self, label, owner ):
        Popup.__init__( self, label, owner )

        self.settingBlock = False

        self.GUI = {}

        self.GUI["mainBox"] = Gtk.VBox()
        self.set_content( self.GUI["mainBox"] )

        #-- Volume --------------------------------------------
        self.GUI["volumeBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["volumeBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["volumeLabel"] = Gtk.Label(label= _("Volume") + ':' )
        self.GUI["volumeLabel"].set_size_request( 100, -1 )
        self.GUI["volumeLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["volumeBox"].pack_start(self.GUI["volumeLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["volumeAdjustment"] = Gtk.Adjustment( 0.5, 0.0, 1.0, 0.01, 0.01, 0 )
        self.GUI["volumeAdjustment"].connect( 'value-changed', self.handleVolume )
        self.GUI["volumeSlider"] = Gtk.HScale( adjustment = self.GUI["volumeAdjustment"] )
        self.GUI["volumeSlider"].set_size_request( 250, -1 )
        self.GUI["volumeSlider"].set_draw_value( True )
        self.GUI["volumeSlider"].set_digits( 2 )
        self.GUI["volumeSlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["volumeBox"].pack_start(self.GUI["volumeSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["volumeImage"] = Gtk.Image()
        self.GUI["volumeBox"].pack_start(self.GUI["volumeImage"], False, True,
                padding=style.DEFAULT_PADDING)

        #-- Pan -----------------------------------------------
        self.GUI["panBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["panBox"], True, True,
                padding = style.DEFAULT_PADDING)
        self.GUI["panLabel"] = Gtk.Label(label= _("Pan:") )
        self.GUI["panLabel"].set_size_request( 100, -1 )
        self.GUI["panLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["panBox"].pack_start(self.GUI["panLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["panAdjustment"] = Gtk.Adjustment( 0.5, 0, 1.0, 0.01, 0.01, 0 )
        self.GUI["panAdjustment"].connect( 'value-changed', self.handlePan )
        self.GUI["panSlider"] = Gtk.HScale( adjustment = self.GUI["panAdjustment"] )
        self.GUI["panSlider"].set_size_request( 250, -1 )
        self.GUI["panSlider"].set_draw_value( True )
        self.GUI["panSlider"].set_digits( 2 )
        self.GUI["panSlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["panBox"].pack_start(self.GUI["panSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["panImage"] = Gtk.Image()
        self.GUI["panBox"].pack_start(self.GUI["panImage"], False, True,
                padding=style.DEFAULT_PADDING)

        #-- Reverb --------------------------------------------
        self.GUI["reverbBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["reverbBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["reverbLabel"] = Gtk.Label(label= _("Reverb") + ':' )
        self.GUI["reverbLabel"].set_size_request( 100, -1 )
        self.GUI["reverbLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["reverbBox"].pack_start(self.GUI["reverbLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["reverbAdjustment"] = Gtk.Adjustment( 0.5, 0, 1.0, 0.01, 0.01, 0 )
        self.GUI["reverbAdjustment"].connect( 'value-changed', self.handleReverb )
        self.GUI["reverbSlider"] = Gtk.HScale( adjustment = self.GUI["reverbAdjustment"] )
        self.GUI["reverbSlider"].set_size_request( 250, -1 )
        self.GUI["reverbSlider"].set_draw_value( True )
        self.GUI["reverbSlider"].set_digits( 2 )
        self.GUI["reverbSlider"].set_value_pos(Gtk.PositionType.RIGHT)
        self.GUI["reverbBox"].pack_start(self.GUI["reverbSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["reverbImage"] = Gtk.Image()
        self.GUI["reverbBox"].pack_start(self.GUI["reverbImage"], False, True,
                padding=style.DEFAULT_PADDING)

        if False: # TEMP quote out
            self.GUI["separator"] = Gtk.HSeparator()
            self.GUI["mainBox"].pack_start(self.GUI["separator"], True, True,
                    padding=style.DEFAULT_PADDING)

            #-- Export --------------------------------------------
            self.GUI["exportBox"] = Gtk.HBox()
            self.GUI["mainBox"].pack_start(self.GUI["exportBox"], True, True,
                    padding=style.DEFAULT_PADDING)
            self.GUI["exportEntry"] = Gtk.Entry()
            self.GUI["exportEntry"].modify_fg( Gtk.StateType.NORMAL, self.owner.colors["black"] )
            self.GUI["exportEntry"].modify_fg( Gtk.StateType.ACTIVE, self.owner.colors["black"] )
            self.GUI["exportBox"].pack_start(self.GUI["exportEntry"], True,
                    True, padding=style.DEFAULT_PADDING)
            self.GUI["exportButton"] = Gtk.Button( "Export" )
            self.GUI["exportBox"].pack_start(self.GUI["exportButton"], False,
                    True, padding=style.DEFAULT_PADDING)

        self.GUI["mainBox"].show_all()

    def setBlock( self, block ):
        self.settingBlock = True

        self.block = block
        self.GUI["volumeAdjustment"].set_value( block.getData( "volume" ) )
        self.GUI["panAdjustment"].set_value( block.getData( "pan" ) )
        self.GUI["reverbAdjustment"].set_value( block.getData( "reverb" ) )
        #self.GUI["exportEntry"].set_text( block.getData( "name" ) )

        self.settingBlock = False

        Popup.setBlock( self, block )

    def handleVolume( self, widget ):
        if not self.settingBlock:
            self.block.setData( "volume", widget.get_value() )

    def handlePan( self, widget ):
        if not self.settingBlock:
            self.block.setData( "pan", widget.get_value() )

    def handleReverb( self, widget ):
        if not self.settingBlock:
            self.block.setData( "reverb", widget.get_value() )


class Drum( Popup ):

    def __init__( self, label, owner ):
        Popup.__init__( self, label, owner )

        self.settingBlock = False

        self.GUI = {}

        self.GUI["mainBox"] = Gtk.VBox()
        self.set_content( self.GUI["mainBox"] )

        #-- Volume --------------------------------------------
        self.GUI["volumeBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start( self.GUI["volumeBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["volumeLabel"] = Gtk.Label(label= _("Volume") + ':' )
        self.GUI["volumeLabel"].set_size_request( 130, -1 )
        self.GUI["volumeLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["volumeBox"].pack_start(self.GUI["volumeLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["volumeAdjustment"] = Gtk.Adjustment( 0.5, 0.0, 1.0, 0.01, 0.01, 0 )
        self.GUI["volumeAdjustment"].connect( 'value-changed', self.handleVolume )
        self.GUI["volumeSlider"] = Gtk.HScale( adjustment = self.GUI["volumeAdjustment"] )
        self.GUI["volumeSlider"].set_size_request( 250, -1 )
        self.GUI["volumeSlider"].set_draw_value( True )
        self.GUI["volumeSlider"].set_digits( 2 )
        self.GUI["volumeSlider"].set_value_pos(Gtk.PositionType.RIGHT)
        self.GUI["volumeBox"].pack_start(self.GUI["volumeSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["volumeImage"] = Gtk.Image()
        self.GUI["volumeBox"].pack_start(self.GUI["volumeImage"], False, True,
                padding=style.DEFAULT_PADDING)

        #-- Reverb --------------------------------------------
        self.GUI["reverbBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["reverbBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["reverbLabel"] = Gtk.Label(label= _("Reverb") + ':' )
        self.GUI["reverbLabel"].set_size_request( 130, -1 )
        self.GUI["reverbLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["reverbBox"].pack_start(self.GUI["reverbLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["reverbAdjustment"] = Gtk.Adjustment( 0.5, 0, 1.0, 0.01, 0.01, 0 )
        self.GUI["reverbAdjustment"].connect( 'value-changed', self.handleReverb )
        self.GUI["reverbSlider"] = Gtk.HScale( adjustment = self.GUI["reverbAdjustment"] )
        self.GUI["reverbSlider"].set_size_request( 250, -1 )
        self.GUI["reverbSlider"].set_draw_value( True )
        self.GUI["reverbSlider"].set_digits( 2 )
        self.GUI["reverbSlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["reverbBox"].pack_start(self.GUI["reverbSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["reverbImage"] = Gtk.Image()
        self.GUI["reverbBox"].pack_start(self.GUI["reverbImage"], False, True,
                padding=style.DEFAULT_PADDING)

        self.GUI["generationSeparator"] = Gtk.HSeparator()
        self.GUI["mainBox"].pack_start(self.GUI["generationSeparator"], True,
                True, padding=style.DEFAULT_PADDING)

        #-- Beats ---------------------------------------------
        self.GUI["beatsBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["beatsBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["beatsLabel"] = Gtk.Label(label= _("Beats:") )
        self.GUI["beatsLabel"].set_size_request( 130, -1 )
        self.GUI["beatsLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["beatsBox"].pack_start(self.GUI["beatsLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["beatsAdjustment"] = Gtk.Adjustment( 4, 2, Config.MAXIMUM_BEATS, 1, 1, 0 )
        self.GUI["beatsAdjustment"].connect( 'value-changed', self.handleBeats )
        self.GUI["beatsSlider"] = Gtk.HScale( adjustment = self.GUI["beatsAdjustment"] )
        self.GUI["beatsSlider"].set_size_request( 250, -1 )
        self.GUI["beatsSlider"].set_draw_value( True )
        self.GUI["beatsSlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["beatsSlider"].set_digits(0)
        self.GUI["beatsBox"].pack_start(self.GUI["beatsSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["beatsImage"] = Gtk.Image()
        self.GUI["beatsBox"].pack_start(self.GUI["beatsImage"], False, True,
                padding=style.DEFAULT_PADDING)

        #-- Regularity ----------------------------------------
        self.GUI["regularityBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["regularityBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["regularityLabel"] = Gtk.Label(label= _("Regularity:") )
        self.GUI["regularityLabel"].set_size_request( 130, -1 )
        self.GUI["regularityLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["regularityBox"].pack_start(self.GUI["regularityLabel"],
                False, True, padding = style.DEFAULT_PADDING)
        self.GUI["regularityAdjustment"] = Gtk.Adjustment( 0.8, 0.0, 1.0, 0.01, 0.01, 0 )
        self.GUI["regularityAdjustment"].connect( 'value-changed', self.handleRegularity )
        self.GUI["regularitySlider"] = Gtk.HScale( adjustment = self.GUI["regularityAdjustment"] )
        self.GUI["regularitySlider"].set_size_request( 250, -1 )
        self.GUI["regularitySlider"].set_draw_value( True )
        self.GUI["regularitySlider"].set_digits( 2 )
        self.GUI["regularitySlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["regularityBox"].pack_start(self.GUI["regularitySlider"],
                False, True, padding=style.DEFAULT_PADDING)
        self.GUI["regularityImage"] = Gtk.Image()
        self.GUI["regularityBox"].pack_start( self.GUI["regularityImage"],
                False, True, padding=style.DEFAULT_PADDING)

        #-- Generate ------------------------------------------
        self.GUI["generateBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start( self.GUI["generateBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["regenerateButton"] = Gtk.Button( "Regenerate" )
        self.GUI["regenerateButton"].connect( "clicked", self.handleRegenerate )
        self.GUI["generateBox"].pack_start(self.GUI["regenerateButton"], True,
                False, padding=style.DEFAULT_PADDING)
        self.GUI["clearButton"] = Gtk.Button( "Clear" )
        self.GUI["clearButton"].connect( "clicked", self.handleClear )
        self.GUI["generateBox"].pack_start(self.GUI["clearButton"], True,
                False, padding=style.DEFAULT_PADDING)

        self.GUI["mainBox"].show_all()

    def setBlock( self, block ):
        self.settingBlock = True

        self.block = block
        self.GUI["volumeAdjustment"].set_value( block.getData( "volume" ) )
        self.GUI["reverbAdjustment"].set_value( block.getData( "reverb" ) )
        self.GUI["beatsAdjustment"].set_value( block.getData( "beats" ) )
        self.GUI["regularityAdjustment"].set_value( block.getData( "regularity" ) )

        self.settingBlock = False

        Popup.setBlock( self, block )

    def handleVolume( self, widget ):
        if not self.settingBlock:
            self.block.setData( "volume", widget.get_value() )

    def handleReverb( self, widget ):
        if not self.settingBlock:
            self.block.setData( "reverb", widget.get_value() )

    def handleBeats( self, widget ):
        # snap to 0 decimal places
        val = widget.get_value()
        if round( val ) != val:
            widget.set_value( round( val ) )
            return

        if not self.settingBlock:
            self.block.setData( "beats", int(round( widget.get_value() )) )

    def handleRegularity( self, widget ):
        if not self.settingBlock:
            self.block.setData( "regularity", widget.get_value() )

    def handleRegenerate( self, widget ):
        self.block.regenerate()

    def handleClear( self, widget ):
        self.block.clear()

class Loop( Popup ):

    def __init__( self, label, owner ):
        Popup.__init__( self, label, owner )

        self.settingBlock = False

        self.colors = self.owner.colors
        # TODO: gtk3 masks not available yet
        #self.sampleNoteMask = self.owner.sampleNoteMask

        self.noteDB = self.owner.noteDB
        self.csnd = new_csound_client()

        self.GUI = {}

        self.GUI["mainBox"] = Gtk.VBox()
        self.set_content( self.GUI["mainBox"] )

        #-- Beats ---------------------------------------------
        self.GUI["beatsBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["beatsBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["beatsLabel"] = Gtk.Label(label= _("Beats:") )
        self.GUI["beatsLabel"].set_size_request( 130, -1 )
        self.GUI["beatsLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["beatsBox"].pack_start(self.GUI["beatsLabel"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["beatsAdjustment"] = Gtk.Adjustment( 4, 2, Config.MAXIMUM_BEATS, 1, 1, 0 )
        self.GUI["beatsAdjustment"].connect( 'value-changed', self.handleBeats )
        self.GUI["beatsSlider"] = Gtk.HScale( adjustment = self.GUI["beatsAdjustment"] )
        self.GUI["beatsSlider"].set_size_request( 250, -1 )
        self.GUI["beatsSlider"].set_draw_value( True )
        self.GUI["beatsSlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["beatsSlider"].set_digits( 0 )
        self.GUI["beatsBox"].pack_start(self.GUI["beatsSlider"], False, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["beatsImage"] = Gtk.Image()
        self.GUI["beatsBox"].pack_start(self.GUI["beatsImage"], False, True,
                padding=style.DEFAULT_PADDING)

        #-- Regularity ----------------------------------------
        self.GUI["regularityBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["regularityBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["regularityLabel"] = Gtk.Label(label= _("Regularity:") )
        self.GUI["regularityLabel"].set_size_request( 130, -1 )
        self.GUI["regularityLabel"].set_alignment( 0.0, 0.5 )
        self.GUI["regularityBox"].pack_start(self.GUI["regularityLabel"],
                False, True, padding=style.DEFAULT_PADDING)
        self.GUI["regularityAdjustment"] = Gtk.Adjustment( 0.8, 0.0, 1.0, 0.01, 0.01, 0 )
        self.GUI["regularityAdjustment"].connect( 'value-changed', self.handleRegularity )
        self.GUI["regularitySlider"] = Gtk.HScale( adjustment = self.GUI["regularityAdjustment"] )
        self.GUI["regularitySlider"].set_size_request( 250, -1 )
        self.GUI["regularitySlider"].set_draw_value( True )
        self.GUI["regularitySlider"].set_digits( 2 )
        self.GUI["regularitySlider"].set_value_pos( Gtk.PositionType.RIGHT )
        self.GUI["regularityBox"].pack_start(self.GUI["regularitySlider"],
                False, True, padding=style.DEFAULT_PADDING)
        self.GUI["regularityImage"] = Gtk.Image()
        self.GUI["regularityBox"].pack_start( self.GUI["regularityImage"],
                False, True, padding=style.DEFAULT_PADDING)

        #-- Generate ------------------------------------------
        self.GUI["generateBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start( self.GUI["generateBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["regenerateButton"] = Gtk.Button( "Regenerate" )
        self.GUI["regenerateButton"].connect( "clicked", self.handleRegenerate )
        self.GUI["generateBox"].pack_start(self.GUI["regenerateButton"], True,
                False, padding=style.DEFAULT_PADDING)
        self.GUI["clearButton"] = Gtk.Button( "Clear" )
        self.GUI["clearButton"].connect( "clicked", self.handleClear )
        self.GUI["generateBox"].pack_start(self.GUI["clearButton"], True,
                False, padding=style.DEFAULT_PADDING)
        self.GUI["recordButton"] = Gtk.ToggleButton( "Record" )
        self.GUI["recordButton"].connect( "toggled", self.handleRecord )
        self.GUI["generateBox"].pack_start(self.GUI["recordButton"], True,
                False, padding=style.DEFAULT_PADDING)

        #-- Preview -------------------------------------------
        self.GUI["previewBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["previewBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["previewEventBox"] = Gtk.EventBox()
        self.GUI["previewEventBox"].add_events(Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.GUI["previewEventBox"].connect( "button-press-event", self.handlePreviewPress )
        self.GUI["previewEventBox"].connect( "button-release-event", self.handlePreviewRelease )
        self.GUI["previewEventBox"].connect( "motion-notify-event", self.handlePreviewMotion )
        self.GUI["previewEventBox"].connect( "leave-notify-event", self.handlePreviewLeave )
        self.GUI["previewBox"].pack_start(self.GUI["previewEventBox"], True,
                True, padding=style.DEFAULT_PADDING)
        self.previewDA = self.GUI["previewDA"] = Gtk.DrawingArea()
        self.GUI["previewDA"].connect( "size-allocate", self.handlePreviewAlloc )
        self.GUI["previewDA"].connect("draw", self.__draw_cb)
        self.GUI["previewEventBox"].add( self.GUI["previewDA"] )

        self.GUI["mainBox"].show_all()

        self.previewDA.alloced = False
        self.previewDirty = False
        self.previewDirtyRect = ( 0, 0, 0, 0 )
        self.dirtyRectToAdd = ( 0, 0, 0, 0 )

        self.sampleBg = self.owner.sampleBg
        self.GUI["previewDA"].set_size_request(-1, self.sampleBg.get_height())
        self.sampleNoteHeight = self.owner.sampleNoteHeight
        # TODO: gtk3 Masks not available yet
        #self.sampleNoteMask = self.owner.sampleNoteMask

        self.pitchPerPixel = float(Config.NUMBER_OF_POSSIBLE_PITCHES-1) / \
                (self.sampleBg.get_height() - self.sampleNoteHeight)
        self.pixelsPerPitch = float(self.sampleBg.get_height() - \
                self.sampleNoteHeight) / (Config.MAXIMUM_PITCH - \
                Config.MINIMUM_PITCH)
        # Temporary Initialization
        self.pixelsPerTick = [0] + [ 1 for i in range(1,Config.MAXIMUM_BEATS+1) ]
        self.ticksPerPixel = [0] + [ 1 for i in range(1,Config.MAXIMUM_BEATS+1) ]

        self.cursor = {"default": None,
            "drag-onset": Gdk.Cursor.new(Gdk.CursorType.SB_RIGHT_ARROW),
            "drag-pitch": Gdk.Cursor.new(Gdk.CursorType.BOTTOM_SIDE),
            "drag-duration": Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE),
            "drag-playhead": Gdk.Cursor.new(Gdk.CursorType.SB_H_DOUBLE_ARROW),
            "pencil": Gdk.Cursor.new(Gdk.CursorType.PENCIL),
            "paste": Gdk.Cursor.new(Gdk.CursorType.CENTER_PTR),
            "error": None}

        self.recording = False
        self.recordLoop = None
        self.recordingNote = None
        self.grid = Config.DEFAULT_GRID

        self.activeTrack = 0 # which track notes are being edited/displayed on

        self.owner.noteDB.addListener( self, LoopParasite )

    def destroy( self ):
        self.owner.noteDB.deleteListener( self )

        Popup.destroy()

    def setBlock( self, block ):
        self.settingBlock = True

        if self.GUI["recordButton"].get_active():
            self.GUI["recordButton"].set_active( False )

        if self.block != None:
            self.applyNoteSelection( SELECTNOTES.NONE, 0, [], self.curPage )

        self.block = block
        self.GUI["beatsAdjustment"].set_value( block.getData( "beats" ) )
        self.GUI["regularityAdjustment"].set_value( block.getData( "regularity" ) )

        root = block.getRoot()
        if root.type == Block.Instrument:
            self.instrument = { "id":        root.getData( "id" ),
                                "amplitude": root.getData( "volume" ),
                                "pan":       root.getData( "pan" ),
                                "reverb":    root.getData( "reverb" ) }
        else:
            self.instrument = self.owner.getInstrument()

        self.curPage = block.getData("id")
        self.curBeats = block.getData("beats")

        self.selectedNotes = [ [] for i in range(Config.NUMBER_OF_TRACKS) ]

        self.curAction = False          # stores the current mouse action
        self.curActionObject = False    # stores the object that in handling the action

        self.lastDO = self.lastDP = self.lastDrumDP = self.lastDD = None

        self.clickButton = 0        # used in release and motion events to make sure we where actually the widget originally clicked. (hack for popup windows)
        self.buttonPressCount = 1   # used on release events to indicate double/triple releases
        self.clickLoc = [0,0]       # location of the last click
        self.marqueeLoc = False     # current drag location of the marquee
        self.marqueeRect = [[0,0],[0,0]]

        self.playheadT = 0
        self.playheadX = Config.TRACK_SPACING_DIV2

        self.settingBlock = False

        if self.previewDA.alloced:
            self.invalidatePreview( 0, 0, self.previewDA.width, self.previewDA.height, -1, True )

        Popup.setBlock( self, block )

    def popdown( self, immediate = False ):
        self.applyNoteSelection( SELECTNOTES.NONE, 0, [], self.curPage )

        if self.GUI["recordButton"].get_active():
            self.GUI["recordButton"].set_active( False )

        Popup.popdown( self, immediate )

    def getPage( self ):
        if self.block != None:
            return self.block.getData("id")
        else:
            return -1

    #=======================================================
    # Handelers

    def handleBeats( self, widget ):
        # snap to 0 decimal places
        val = widget.get_value()
        if round( val ) != val:
            widget.set_value( round( val ) )
            return

        if not self.settingBlock:
            self.curBeats = int(round( widget.get_value() ))
            self.block.setData( "beats", self.curBeats )
            for n in self.owner.noteDB.getNotesByTrack( self.getPage(), self.activeTrack, self ):
                n.updateTransform( True )
            self.invalidatePreview( 0, 0, self.previewDA.width, self.previewDA.height )

        if self.recordLoop:
            self.owner.removeMetronome( self.curPage )
            self.owner.addMetronome( self.curPage, self.grid )
            self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def handleRegularity( self, widget ):
        if not self.settingBlock:
            self.block.setData( "regularity", widget.get_value() )

    def handleRegenerate( self, widget ):
        parameters = GenerationParameters(
            density = [0.9 for x in range(4)],
            rythmRegularity = [self.block.getData( "regularity" ) for x in range(4)],
            step = [0.5 for x in range(4)],
            pitchRegularity = [0. for x in range(4)],
            articule = [1. for x in range(4)],
            silence = [0.1 for x in range(4)],
            pattern = [3 for x in range(4)],
            scale = GenerationConstants.NATURAL_MINOR)

        self.owner._generateTrack( self.instrument["id"], self.curPage, self.activeTrack, parameters, generator1 )

        self.block.updateLoop()
        if self.recordLoop:
            self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def handleClear( self, widget ):
        if self.recording:
            self.noteDB.deleteNotesByTrack( [ self.curPage ], [ 2 ] )
        else:
            self.block.clear()

        if self.recordLoop:
            self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def handleRecord( self, widget ):
        if widget.get_active():
            self.startRecording()
        else:
            self.stopRecording()

    def handlePreviewPress( self, widget, event ):
        if event.button != 1:
            return

        self.clickButton = event.button

        if event.type == Gdk._2BUTTON_PRESS:   self.buttonPressCount = 2
        elif event.type == Gdk._3BUTTON_PRESS: self.buttonPressCount = 3
        else:                                      self.buttonPressCount = 1

        self.clickLoc = [ int(event.x), int(event.y) ]

        page = self.block.getData("id")
        beats = self.block.getData("beats")

        notes = self.noteDB.getNotesByTrack( page, self.activeTrack, self )
        last = len(notes)-1
        handled = 0
        for n in range(last+1):
            handled = notes[n].handleButtonPress( self, event )
            if handled == 0:
                continue
            elif handled == 1:
                if not self.curAction: self.curAction = True # it was handled but no action was declared, set curAction to True anyway
                return
            else:      # all other options mean we can stop looking
                break

        if not handled or handled == -1:  # event didn't overlap any notes, so we can draw
            pitch = min( self.pixelsToPitchFloor( self.clickLoc[1] - self.previewDA.height + self.sampleNoteHeight//2 ), Config.NUMBER_OF_POSSIBLE_PITCHES-1) + Config.MINIMUM_PITCH
            onset = self.pixelsToTicksFloor( beats, self.clickLoc[0] )
            cs = CSoundNote( onset,
                             pitch,
                             0.75,
                             0.5,
                             1,
                             self.activeTrack,
                             instrumentId = self.instrument["id"] )
            cs.pageId = page
            id = self.noteDB.addNote( -1, page, self.activeTrack, cs )
            n = self.noteDB.getNote( page, self.activeTrack, id, self )
            self.selectNotes( { self.activeTrack:[n] }, True )
            n.playSampleNote( False )

            noteS = self.noteDB.getNotesByTrack( page, self.activeTrack )
            for note in noteS:
                if note.cs.onset < onset and (note.cs.onset + note.cs.duration) > onset:
                    self.noteDB.updateNote(self.curPage, self.activeTrack, note.id, PARAMETER.DURATION, onset - note.cs.onset)

            self.updateDragLimits()
            self.clickLoc[0] += self.ticksToPixels( beats, 1 )
            self.setCurrentAction( "note-drag-duration", n )
            self.setCursor("drag-duration")

    def handlePreviewRelease( self, widget, event ):
        if not self.clickButton: return # we recieved this event but were never clicked! (probably a popup window was open)
        self.clickButton = 0

        if event.button != 1:
            return

        if not self.curAction:
            self.applyNoteSelection( SELECTNOTES.NONE, self.activeTrack, [], self.curPage )
            return

        if not self.curActionObject: # there was no real action to carry out
            self.curAction = False
            return

        if self.curActionObject != self:
            self.curActionObject.handleButtonRelease( self, event, self.buttonPressCount )
            self.updateTooltip( event )
        else:
            # we're doing the action ourselves
            if self.curAction == "marquee":         self.doneMarquee( event )
            self.updateTooltip( event )

    def handlePreviewMotion( self, widget, event ):
        if event.is_hint:
            x, y, state = self.previewDA.get_window().get_pointer()
            event.x = float(x)
            event.y = float(y)
            event.state = state

        if not self.clickButton: # we recieved this event but were never clicked! (probably a popup window was open)
            self.updateTooltip( event )
            return

        if event.get_state() & Gdk.ModifierType.BUTTON1_MASK:
            if not self.curAction: # no action is in progress yet we're dragging, start a marquee
                self.setCurrentAction( "marquee", self )

            if self.curAction == "note-drag-onset":
                self.noteDragOnset( event )

            elif self.curAction == "note-drag-duration":
                self.noteDragDuration( event )

            elif self.curAction == "note-drag-pitch":
                self.noteDragPitch( event )

            #elif self.curAction == "note-drag-pitch-drum":
            #    self.noteDragPitch( event, True )

            elif self.curAction == "marquee":
                self.updateMarquee( event )
        else:
            self.updateTooltip( event )

    def handlePreviewLeave( self, widget, event ):
        self.setCursor("default")

    def handlePreviewAlloc( self, widget, allocation ):
        self.previewDA.alloced = True
        win = Gdk.get_default_root_window()
        self.previewDA.width = allocation.width
        self.previewDA.height = allocation.height
        self.previewBuffer = Gdk.Pixmap( win, allocation.width, allocation.height )
        self.clearClipMask = ( 0, 0, allocation.width, allocation.height )

        self.pixelsPerTick = [0] + [ self.previewDA.width/float(i*Config.TICKS_PER_BEAT) for i in range(1,Config.MAXIMUM_BEATS+1) ]
        self.ticksPerPixel = [0] + [ 1.0/self.pixelsPerTick[i] for i in range(1,Config.MAXIMUM_BEATS+1) ]

        self.beatSpacing = [[0]]
        for i in range(1,Config.MAXIMUM_BEATS+1):
            self.beatSpacing.append( [ self.ticksToPixels( i, Config.TICKS_PER_BEAT*j ) for j in range(i) ] )

        for n in self.owner.noteDB.getNotes( self ):
            n.updateTransform( True )

        self.invalidatePreview( 0, 0, allocation.width, allocation.height, -1, True )

    def on_key_press( self, widget, event ):
        keyval = event.keyval

        # backspace and del keys
        if keyval == Gdk.KEY_Delete or keyval == Gdk.KEY_BackSpace:
            if len( self.selectedNotes[0] ):
                self.owner.noteDB.deleteNotes(
                    [ self.curPage, self.activeTrack, len( self.selectedNotes[0] ) ]
                  + [ n.note.id for n in self.selectedNotes[0] ]
                  + [ -1 ] )
            self.block.updateLoop()
            if self.recordLoop:
                self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

        else:
            self.owner.onKeyPress( widget, event )

    #=======================================================
    # Drawing

    def previewDraw( self ):
        startX = self.previewDirtyRect.x
        startY = self.previewDirtyRect.y
        stopX = self.previewDirtyRect.x + self.previewDirtyRect.width
        stopY = self.previewDirtyRect.y + self.previewDirtyRect.height

        page = self.block.getData("id")
        beats = self.owner.noteDB.getPage(page).beats

        self.gc.set_clip_rectangle( self.previewDirtyRect )

        # draw background
        self.previewBuffer.draw_drawable( self.gc, self.sampleBg, 0, 0, 0, 0, self.previewDA.width-5, self.previewDA.height )
        self.previewBuffer.draw_drawable( self.gc, self.sampleBg, self.sampleBg.get_width() - 5, 0, self.previewDA.width-5, 0, 5, self.previewDA.height )

        # draw beat lines
        self.gc.set_line_attributes( Config.BEAT_LINE_SIZE, Gdk.LINE_ON_OFF_DASH, Gdk.CAP_BUTT, Gdk.JOIN_MITER )
        self.gc.foreground = self.colors["Beat_Line"]
        for i in range(1,beats):
            x = self.beatSpacing[beats][i]
            self.previewBuffer.draw_line( self.gc, x, 1, x, self.previewDA.height-1 )

        # draw notes
        self.gc.set_clip_mask( self.sampleNoteMask )
        notes = self.owner.noteDB.getNotesByTrack( page, self.activeTrack, self )
        for n in notes:
            # TODO:
            # LoopParasite changed signature to (ctx, x, y)
            if not n.draw( self.previewBuffer, self.gc, startX, stopX ): break

        self.previewDirty = False

    def __draw_cb(self, widget, ctx):
        if self.previewDirty:
            self.previewDraw()

        # draw base
        #Gtk.DrawingArea.do_draw(self, ctx)

        # draw the selection rect
        if self.marqueeLoc:
            ctx.save()
            ctx.set_line_width(Config.MARQUEE_SIZE)
            ctx.set_dash((10,10))  # Gdk.LINE_ON_OFF_DASH equivalent?
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
            ctx.set_line_join(cairo.LINE_JOIN_MITER)
            ctx.set_source_rgb(CairoUtil.gdk_color_to_cairo(
                    self.colors["Preview_Note_Selected"]))
            ctx.rectangle(self.marqueeRect[0][0], self.marqueeRect[0][1],
                    self.marqueeRect[1][0], self.marqueeRect[1][1])
            ctx.stroke()
            ctx.restore()

        if self.recording: # draw playhead
            ctx.save()
            ctx.set_line_width(Config.PLAYHEAD_SIZE)
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
            ctx.set_line_join(cairo.LINE_JOIN_MITER)
            ctx.set_source_rgb(CairoUtil.gdk_color_to_cairo(
                    self.colors["black"]))
            # TODO: event properties is not available anymore
            # use clipping?
            ctx.rectangle(self.playheadX, event.area.y, self.playheadX,
                    event.area.y + event.area.height)
            ctx.stroke()
            ctx.restore()

    def invalidatePreview( self, x, y, width, height, page = -1, base = True ):
        if page != -1 and page != self.getPage():
            return

        self.dirtyRectToAdd.x = x
        self.dirtyRectToAdd.y = y
        self.dirtyRectToAdd.width = width
        self.dirtyRectToAdd.height = height

        if base: # the base image has been dirtied
            if not self.previewDirty:
                self.previewDirtyRect.x = x
                self.previewDirtyRect.y = y
                self.previewDirtyRect.width = width
                self.previewDirtyRect.height = height
            else:
               self.previewDirtyRect = self.previewDirtyRect.union( self.dirtyRectToAdd )
            self.previewDirty = True

        if self.previewDA.get_window() != None:
            self.previewDA.get_window().invalidate_rect(self.dirtyRectToAdd,
                    True)

    #=======================================================
    # Recording

    def startRecording( self ):
        if self.recording:
            return

        self.changedMute = self.owner._setMuted( True )
        self.owner.pushInstrument( self.instrument )
        self.owner.setKeyboardListener( self )

        self.owner.addMetronome( self.curPage, self.grid )

        # record to scratch track
        self.owner.noteDB.tracksToClipboard( [ self.curPage ], [ 0 ] )
        self.owner.noteDB.pasteClipboard( [ self.curPage ], 0, { 2:0 }, { 2:self.instrument["id"] } )
        self.activeTrack = 2

        self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], force = True, sync = False )
        self.updatePlayhead()
        self.recordTimeout = GObject.timeout_add( 20, self._record_timeout )
        self.recording = True

    def stopRecording( self ):
        if not self.recording:
            return

        GObject.source_remove( self.recordTimeout )
        self.recording = False

        if self.recordingNote:
            self.finishNote()

        self.owner.removeMetronome( self.curPage )

        # copy scratch track back to default track
        self.noteDB.deleteNotesByTrack( [ self.curPage ], [ 0 ] )
        self.owner.noteDB.tracksToClipboard( [ self.curPage ], [ 2 ] )
        self.owner.noteDB.pasteClipboard( [ self.curPage ], 0, { 0:2 } )
        self.noteDB.deleteNotesByTrack( [ self.curPage ], [ 2 ] )
        self.activeTrack = 0
        self.block.updateLoop()

        self.owner._stopLoop( self.recordLoop )
        self.recordLoop = None
        self.clearPlayhead()

        self.owner.popInstrument()
        self.owner.setKeyboardListener( None )
        if self.changedMute:
            self.owner._setMuted( False )
            self.changedMute = False

    def recordNote( self, pitch ):
        page = self.block.getData("id")
        ticks = self.owner.noteDB.getPage(page).ticks

        onset = self.csnd.loopGetTick( self.recordLoop )
        onset = self.grid * int( onset/self.grid + 0.5 )
        if   onset < 0:     onset += ticks
        elif onset >= ticks: onset -= ticks
        self.recordingNotePassed = False

        cs = CSoundNote( onset,
                         pitch,
                         0.75,
                         0.5,
                         self.grid,
                         2,
                         instrumentId = self.instrument["id"] )
        cs.pageId = self.curPage

        for n in self.noteDB.getNotesByTrack( self.curPage, 2 )[:]:
            if onset < n.cs.onset:
                break
            if onset >= n.cs.onset + n.cs.duration:
                continue
            if n.cs.onset < onset and n.cs.duration > self.grid:
                self.noteDB.updateNote( n.page, n.track, n.id, PARAMETER.DURATION, onset - n.cs.onset )
            else:
                self.noteDB.deleteNote( n.page, n.track, n.id )

        self.recordingNote = self.noteDB.addNote( -1, self.curPage, 2, cs )

        self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def finishNote( self ):
        self.recordingNote = None

        self.block.updateLoop()
        if self.recordLoop:
            self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def _updateNote( self ):
        page = self.block.getData("id")
        ticks = self.owner.noteDB.getPage(page).ticks

        tick = self.csnd.loopGetTick( self.recordLoop )
        tick = self.grid * int( tick/self.grid + 0.5 )
        if   tick < 0:     tick += ticks
        elif tick >= ticks: tick -= ticks


        note = self.noteDB.getNote( self.curPage, self.activeTrack, self.recordingNote )

        if tick > note.cs.onset:
            self.recordingNotePassed = True

        if self.recordingNotePassed and tick < note.cs.onset:
            tick = self.noteDB.getPage( self.curPage ).ticks
            self.noteDB.updateNote( note.page, note.track, note.id, PARAMETER.DURATION, tick - note.cs.onset )
            for n in self.noteDB.getNotesByTrack( self.curPage, self.activeTrack ):
                if n.cs.onset <= note.cs.onset:
                    continue
                if n.cs.onset < note.cs.onset + note.cs.duration:
                    self.noteDB.deleteNote( n.page, n.track, n.id )
                else:
                    break
            self.finishNote()
        elif tick > note.cs.onset + note.cs.duration:
            self.noteDB.updateNote( note.page, note.track, note.id, PARAMETER.DURATION, tick - note.cs.onset )
            for n in self.noteDB.getNotesByTrack( self.curPage, self.activeTrack ):
                if n.cs.onset <= note.cs.onset:
                    continue
                if n.cs.onset < note.cs.onset + note.cs.duration:
                    self.noteDB.deleteNote( n.page, n.track, n.id )
                else:
                    break
            self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def _record_timeout( self ):
        self.updatePlayhead()
        if self.recordingNote:
            self._updateNote()
        return True

    def updatePlayhead( self ):
        ticks = self.csnd.loopGetTick( self.recordLoop )
        if self.playheadT != ticks:
            self.invalidatePreview( self.playheadX-Config.PLAYHEAD_SIZE/2, 0, Config.PLAYHEAD_SIZE, self.previewDA.height, self.curPage, False )
            self.playheadX = self.ticksToPixels( self.curBeats, ticks )
            self.invalidatePreview( self.playheadX-Config.PLAYHEAD_SIZE/2, 0, Config.PLAYHEAD_SIZE, self.previewDA.height, self.curPage, False )
            self.playheadT = ticks

        return True

    def clearPlayhead( self ):
        self.invalidatePreview( self.playheadX-Config.PLAYHEAD_SIZE/2, 0, Config.PLAYHEAD_SIZE, self.previewDA.height, self.curPage, False )

    #=======================================================
    # Actions

    def setCurrentAction( self, action, obj = None ):
        if self.curAction:
            self.doneCurrentAction()

        self.curAction = action
        self.curActionObject = obj

        if   action == "note-drag-onset":      self.updateDragLimits()
        elif action == "note-drag-duration":   self.updateDragLimits()
        elif action == "note-drag-pitch":      self.updateDragLimits()
        #elif action == "note-drag-pitch-drum": self.updateDragLimits()

    def doneCurrentAction( self ):
        if not self.curAction: return
        action = self.curAction
        self.curAction = False

        if   action == "note-drag-onset":      self.doneNoteDrag( action )
        elif action == "note-drag-duration":   self.doneNoteDrag( action )
        elif action == "note-drag-pitch":      self.doneNoteDrag( action )
        #elif action == "note-drag-pitch-drum": self.doneNoteDrag( action )

    def selectionChanged( self ):
        if   self.curAction == "note-drag-onset":      self.updateDragLimits()
        elif self.curAction == "note-drag-duration":   self.updateDragLimits()
        elif self.curAction == "note-drag-pitch":      self.updateDragLimits()
        #elif self.curAction == "note-drag-pitch-drum": self.updateDragLimits()

    def applyNoteSelection( self, mode, trackN, which, page = -1 ):
        if page == -1: page = self.curPage
        if mode == SELECTNOTES.ALL:
            track = self.noteDB.getNotesByTrack( page, trackN, self )
            list(map( lambda note:note.setSelected( True ), track ))
            self.selectedNotes[trackN] = []
            list(map( lambda note:self.selectedNotes[trackN].append(note), track ))
        elif mode == SELECTNOTES.NONE:
            track = self.selectedNotes[trackN] #self.noteDB.getNotesByTrack( page, trackN, self )
            list(map( lambda note:note.setSelected( False ), track ))
            self.selectedNotes[trackN] = []
        elif mode == SELECTNOTES.ADD:
            for note in which:
                if note.setSelected( True ):
                    self.selectedNotes[trackN].append( note )
        elif mode == SELECTNOTES.REMOVE:
            for note in which:
                if note.setSelected( False ):
                    self.selectedNotes[trackN].remove( note )
        elif mode == SELECTNOTES.FLIP:
            for note in which:
                if note.getSelected():
                    note.setSelected( False )
                    self.selectedNotes[trackN].remove( note )
                else:
                    note.setSelected( True )
                    self.selectedNotes[trackN].append( note )
        elif mode == SELECTNOTES.EXCLUSIVE:
            notes = self.noteDB.getNotesByTrack( page, trackN, self )
            for n in range(len(notes)):
                if notes[n] in which:
                    if notes[n].setSelected( True ):
                        self.selectedNotes[trackN].append( notes[n] )
                else:
                    if notes[n].setSelected( False ):
                        self.selectedNotes[trackN].remove( notes[n] )

    def selectNotesByBar( self, trackN, start, stop, page = -1 ):
        for i in range(Config.NUMBER_OF_TRACKS):
            if i == trackN:
                notes = []
                track = self.noteDB.getNotesByTrack( self.curPage, trackN, self )
                for n in range(len(track)):
                    if track[n].testOnset( start, stop ): notes.append(track[n])
                if not Config.ModKeys.ctrlDown: self.applyNoteSelection( SELECTNOTES.EXCLUSIVE, trackN, notes, page )
                else:                           self.applyNoteSelection( SELECTNOTES.ADD, trackN, notes, page )
            else:
                if not Config.ModKeys.ctrlDown: self.applyNoteSelection( SELECTNOTES.NONE, i, [], page )
        self.selectionChanged()

    def selectNotesByTrack( self, trackN, page = -1 ):
        if Config.ModKeys.ctrlDown:
            self.applyNoteSelection( SELECTNOTES.ALL, trackN, [], page )
        else:
            for i in range(Config.NUMBER_OF_TRACKS):
                if i == trackN: self.applyNoteSelection( SELECTNOTES.ALL, trackN, [], page )
                else:           self.applyNoteSelection( SELECTNOTES.NONE, i, [], page )
        self.selectionChanged()

    def selectNotes( self, noteDic, ignoreCtrl = False, page = -1 ):
        if Config.ModKeys.ctrlDown and not ignoreCtrl:
            for i in noteDic:
                self.applyNoteSelection( SELECTNOTES.FLIP, i, noteDic[i], page )
        else:
            for i in range(Config.NUMBER_OF_TRACKS):
                if i in noteDic: self.applyNoteSelection( SELECTNOTES.EXCLUSIVE, i, noteDic[i], page )
                else:            self.applyNoteSelection( SELECTNOTES.NONE, i, [], page )
        self.selectionChanged()

    def deselectNotes( self, noteDic, page = -1 ):
        for i in noteDic:
            self.applyNoteSelection( SELECTNOTES.REMOVE, i, noteDic[i], page )
        self.selectionChanged()

    def clearSelectedNotes( self, page = -1 ):
        for i in range(Config.NUMBER_OF_TRACKS):
            self.applyNoteSelection( SELECTNOTES.NONE, i, [], page )
        self.selectionChanged()

    def updateDragLimits( self ):
        self.dragLimits = [ [-9999,9999], [-9999,9999], [-9999,9999] ] # initialize to big numbers!
        maxRightBound = self.noteDB.getPage(self.curPage).ticks

        for i in range(Config.NUMBER_OF_TRACKS):
            if not len(self.selectedNotes[i]): continue  # no selected notes here

            track = self.noteDB.getNotesByTrack( self.curPage, i, self )
            leftBound = 0
            skip = True # skip the first note
            for n in range(len(track)):
                if skip:
                    skip = False
                    thisNote = track[n]
                    continue
                nextNote = track[n]
                if not thisNote.getSelected():
                    leftBound = thisNote.getEndTick()
                else:
                    if not nextNote.getSelected():
                        rightBound = min( nextNote.getStartTick(), maxRightBound )
                        widthBound = rightBound
                    else:
                        rightBound = maxRightBound
                        widthBound = min( nextNote.getStartTick(), maxRightBound )
                    thisNote.updateDragLimits( self.dragLimits, leftBound, rightBound, widthBound, maxRightBound )
                thisNote = nextNote
            # do the last note
            if thisNote.getSelected():
                thisNote.updateDragLimits( self.dragLimits, leftBound, maxRightBound, maxRightBound, maxRightBound )

    def noteDragOnset( self, event ):
        do = self.pixelsToTicks( self.curBeats, event.x - self.clickLoc[0] )
        do = min( self.dragLimits[0][1], max( self.dragLimits[0][0], do ) )

        if do != self.lastDO:
            self.lastDO = do
            stream = []
            for i in range(Config.NUMBER_OF_TRACKS):
                tstream = []
                for note in self.selectedNotes[i]:
                    note.noteDragOnset( do, tstream )
                if len(tstream):
                    stream += [ self.curPage, i, PARAMETER.ONSET, len(tstream)//2 ] + tstream
            if len(stream):
                self.noteDB.updateNotes( stream + [-1] )

    def noteDragDuration( self, event ):
        dd = self.pixelsToTicks( self.curBeats, event.x - self.clickLoc[0] )
        dd = min( self.dragLimits[2][1], max( self.dragLimits[2][0], dd ) )

        if dd != self.lastDD:
            self.lastDD = dd
            stream = []
            for i in range(Config.NUMBER_OF_TRACKS):
                tstream = []
                for note in self.selectedNotes[i]:
                    note.noteDragDuration( dd, tstream )
                if len(tstream):
                    stream += [ self.curPage, i, PARAMETER.DURATION, len(tstream)//2 ] + tstream
            if len(stream):
                self.noteDB.updateNotes( stream + [-1] )

    def noteDragPitch( self, event, drum = False ):
        if not drum: dp = self.pixelsToPitch( event.y - self.clickLoc[1] )
        else: dp = self.pixelsToPitchDrum( event.y - self.clickLoc[1] )
        dp = min( self.dragLimits[1][1], max( self.dragLimits[1][0], dp ) )

        if dp != self.lastDP:
            self.lastDP = dp
            stream = []
            for i in range(Config.NUMBER_OF_TRACKS):
                tstream = []
                for note in self.selectedNotes[i]:
                    note.noteDragPitch( dp, tstream )
                if len(tstream):
                    stream += [ self.curPage, i, PARAMETER.PITCH, len(tstream)//2 ] + tstream
            if len(stream):
                self.noteDB.updateNotes( stream + [-1] )

            self.curActionObject.playSampleNote( True )

    def doneNoteDrag( self, action ):
       # if action == "note-drag-pitch" or action == "note-drag-pitch-drum":
       #     self.curActionObject.playSampleNote()

        self.lastDO = self.lastDP = self.lastDrumDP = self.lastDD = None

        for i in range(Config.NUMBER_OF_TRACKS):
            for note in self.selectedNotes[i]:
                note.doneNoteDrag( self )

        self.block.updateLoop()
        if self.recordLoop:
            self.recordLoop = self.owner._playLoop( self.instrument["id"], self.instrument["amplitude"], self.instrument["reverb"], [ self.curPage ], self.recordLoop, force = True, sync = False )

    def noteStepOnset( self, step ):
        stream = []
        for i in range(Config.NUMBER_OF_TRACKS):
            if not len(self.selectedNotes[i]): continue  # no selected notes here

            tstream = []
            track = self.noteDB.getNotesByTrack( self.curPage, i, self )
            if step < 0: # moving to the left, iterate forwards
                leftBound = 0
                for n in range(len(track)):
                    leftBound = track[n].noteDecOnset( step, leftBound, tstream )
            else:        # moving to the right, iterate backwards
                rightBound = self.noteDB.getPage(self.curPage).ticks
                for n in range(len(track)-1, -1, -1 ):
                    rightBound = track[n].noteIncOnset( step, rightBound, tstream )

            if len(tstream):
                stream += [ self.curPage, i, PARAMETER.ONSET, len(tstream)//2 ] + tstream

        if len(stream):
            self.noteDB.updateNotes( stream + [-1] )

    def noteStepPitch( self, step ):
        stream = []
        for i in range(Config.NUMBER_OF_TRACKS):
            if not len(self.selectedNotes[i]): continue  # no selected notes here

            tstream = []
            if step < 0:
                for n in self.selectedNotes[i]:
                    n.noteDecPitch( step, tstream )
            else:
                for n in self.selectedNotes[i]:
                    n.noteIncPitch( step, tstream )

            if len(tstream):
                stream += [ self.curPage, i, PARAMETER.PITCH, len(tstream)//2 ] + tstream

        if len(stream):
            self.noteDB.updateNotes( stream + [-1] )

    def noteStepDuration( self, step ):
        stream = []
        for i in range(Config.NUMBER_OF_TRACKS):
            if not len(self.selectedNotes[i]): continue  # no selected notes here

            tstream = []
            if step < 0:
                for n in self.selectedNotes[i]:
                    n.noteDecDuration( step, tstream )
            else:
                track = self.noteDB.getNotesByTrack( self.curPage, i, self )
                for j in range(len(track)-1):
                    track[j].noteIncDuration( step, track[j+1].getStartTick(), tstream )
                track[len(track)-1].noteIncDuration( step, self.noteDB.getPage(self.curPage).ticks, tstream )

            if len(tstream):
                stream += [ self.curPage, i, PARAMETER.DURATION, len(tstream)//2 ] + tstream

        if len(stream):
            self.noteDB.updateNotes( stream + [-1] )

    def noteStepVolume( self, step ):
        stream = []
        for i in range(Config.NUMBER_OF_TRACKS):
            if not len(self.selectedNotes[i]): continue  # no selected notes here

            tstream = []
            if step < 0:
                for n in self.selectedNotes[i]:
                    n.noteDecVolume( step, tstream )
            else:
                for n in self.selectedNotes[i]:
                    n.noteIncVolume( step, tstream )

            if len(tstream):
                stream += [ self.curPage, i, PARAMETER.AMPLITUDE, len(tstream)//2 ] + tstream

        if len(stream):
            self.noteDB.updateNotes( stream + [-1] )

    def updateMarquee( self, event ):
        if self.marqueeLoc:
            oldX = self.marqueeRect[0][0]
            oldEndX = self.marqueeRect[0][0] + self.marqueeRect[1][0]
            oldY = self.marqueeRect[0][1]
            oldEndY = self.marqueeRect[0][1] + self.marqueeRect[1][1]
        else:
            oldX = oldEndX = self.clickLoc[0]
            oldY = oldEndY = self.clickLoc[1]

        self.marqueeLoc = [ int(event.x), int(event.y) ]
        if self.marqueeLoc[0] < 0: self.marqueeLoc[0] = 0
        elif self.marqueeLoc[0] > self.previewDA.width: self.marqueeLoc[0] = self.previewDA.width
        if self.marqueeLoc[1] < 0: self.marqueeLoc[1] = 0
        elif self.marqueeLoc[1] > self.previewDA.height: self.marqueeLoc[1] = self.previewDA.height

        if self.marqueeLoc[0] > self.clickLoc[0]:
            self.marqueeRect[0][0] = self.clickLoc[0]
            self.marqueeRect[1][0] = self.marqueeLoc[0] - self.clickLoc[0]
        else:
            self.marqueeRect[0][0] = self.marqueeLoc[0]
            self.marqueeRect[1][0] = self.clickLoc[0] - self.marqueeLoc[0]
        if self.marqueeLoc[1] > self.clickLoc[1]:
            self.marqueeRect[0][1] = self.clickLoc[1]
            self.marqueeRect[1][1] = self.marqueeLoc[1] - self.clickLoc[1]
        else:
            self.marqueeRect[0][1] = self.marqueeLoc[1]
            self.marqueeRect[1][1] = self.clickLoc[1] - self.marqueeLoc[1]

        x = min( self.marqueeRect[0][0], oldX )
        width = max( self.marqueeRect[0][0] + self.marqueeRect[1][0], oldEndX ) - x
        y = min( self.marqueeRect[0][1], oldY )
        height = max( self.marqueeRect[0][1] + self.marqueeRect[1][1], oldEndY ) - y
        self.invalidatePreview( x-1, y-1, width+2, height+2, self.curPage, False )

    def doneMarquee( self, event ):
        if self.marqueeLoc:
            stop =  [ self.marqueeRect[0][0] + self.marqueeRect[1][0], self.marqueeRect[0][1] + self.marqueeRect[1][1] ]

            select = {}

            intersectionY = [ self.marqueeRect[0][1], stop[1] ]

            notes = []
            track = self.noteDB.getNotesByTrack( self.getPage(), 0, self )
            for n in range(len(track)):
                hit = track[n].handleMarqueeSelect( self,
                                  [ self.marqueeRect[0][0], intersectionY[0] ], \
                                  [ stop[0], intersectionY[1] ] )
                if hit: notes.append(track[n])

            if len(notes): select[0] = notes

            self.selectNotes( select )

        self.marqueeLoc = False
        self.doneCurrentAction()

        self.invalidatePreview( self.marqueeRect[0][0]-1, self.marqueeRect[0][1]-1, self.marqueeRect[1][0]+2, self.marqueeRect[1][1]+2, self.getPage(), False )

    def updateTooltip( self, event ):

        notes = self.noteDB.getNotesByTrack( self.getPage(), self.activeTrack, self )
        handled = 0
        for n in range(len(notes)):
            handled = notes[n].updateTooltip( self, event )
            if handled == 0:   continue
            elif handled == 1: return   # event was handled
            else:              break

        if handled == -2: # event X overlapped with a note
            self.setCursor("default")
            return

        self.setCursor("pencil")

    def setCursor( self, cursor ):
        self.get_window().set_cursor(self.cursor[cursor])

    def ticksToPixels( self, beats, ticks ):
        return int(round( ticks * self.pixelsPerTick[beats] ))
    def pixelsToTicks( self, beats, pixels ):
        return int(round( pixels * self.ticksPerPixel[beats] ))
    def pitchToPixels( self, pitch ):
        return int(round( ( Config.MAXIMUM_PITCH - pitch ) * self.pixelsPerPitch ))
    def ticksToPixelsFloor( self, beats, ticks ):
        return int( ticks * self.pixelsPerTick[beats] )
    def pixelsToTicksFloor( self, beats, pixels ):
        return int( pixels * self.ticksPerPixel[beats] )
    def pixelsToPitch( self, pixels ):
        return int(round(-pixels*self.pitchPerPixel))
    def pitchToPixelsFloor( self, pitch ):
        return int(( Config.MAXIMUM_PITCH - pitch ) * self.pixelsPerPitch )
    def pixelsToPitchFloor( self, pixels ):
        return int(-pixels*self.pitchPerPixel)


class Shortcut( Popup ):

    def __init__( self, label, owner ):
        Popup.__init__( self, label, owner )

        self.GUI = {}

        self.GUI["mainBox"] = Gtk.VBox()
        self.set_content( self.GUI["mainBox"] )

        #-- Keys ----------------------------------------------
        # match keycodes from JamMain.valid_shortcuts
        layout = [ [ 0.0, [ 18, 19, 20, 21 ] ],
                   [ 0.3, [ 32, 33, 34, 35 ] ],
                   [ 1.7, [ 47, 48, 51 ] ],
                   [ 1.1, [ 60, 61 ] ] ]

        self.GUI["keyBox"] = Gtk.VBox()
        self.GUI["mainBox"].pack_start(self.GUI["keyBox"], True, True,
                padding=style.DEFAULT_PADDING - 2)

        for row in layout:
            offset = row[0]
            hbox = Gtk.HBox()
            self.GUI["keyBox"].pack_start(hbox, True, True, padding=2)
            separator = Gtk.Label(label="")
            separator.set_size_request( int(Block.Block.KEYSIZE*row[0]) + style.DEFAULT_PADDING, -1 )
            hbox.pack_start(separator, False, True, 0)
            separator = Gtk.Label(label="")
            separator.set_size_request( style.DEFAULT_PADDING, -1 )
            hbox.pack_end(separator, False, True, 0)
            for key in row[1]:
                self.GUI[key] = Gtk.ToggleButton()
                self.GUI[key].connect("draw", self.__draw_cb)
                self.GUI[key].connect( "toggled", self.keyToggled )
                self.GUI[key].set_size_request( Block.Block.KEYSIZE, Block.Block.KEYSIZE )
                self.GUI[key].key = key
                self.GUI[key].image = [ self.owner.getKeyImage( key, False ),
                                        self.owner.getKeyImage( key, True ) ]
                hbox.pack_start(self.GUI[key], False, True, padding=2)

        #-- None ----------------------------------------------
        self.GUI["noneBox"] = Gtk.HBox()
        self.GUI["mainBox"].pack_start(self.GUI["noneBox"], True, True,
                padding=style.DEFAULT_PADDING)
        self.GUI["noneButton"] = Gtk.Button( _("None") )
        self.GUI["noneButton"].connect( "clicked", self.handleNone )
        self.GUI["noneBox"].pack_start(self.GUI["noneButton"], True, False,
                padding=style.DEFAULT_PADDING)

        self.GUI["mainBox"].show_all()

        self.key = None

    def setBlock( self, block ):
        self.ignoreToggle = True

        self.block = block
        self.key = self.block.getData( "key" )

        if self.key != None:
            self.GUI[self.key].set_active( True )

        self.ignoreToggle = False

        Popup.setBlock( self, block )

    def on_key_press( self, widget, event ):
        key = event.hardware_keycode
        if key in list(self.owner.valid_shortcuts.keys()):
            self.block.setData( "key", key )
            if self.key != None: # clear old key
                self.ignoreToggle = True
                self.GUI[self.key].set_active( False )
                self.key = None
                self.ignoreToggle = False
            self.popdown( True )
        else:
            self.owner.onKeyPress( widget, event )

    def __draw_cb(self, widget, ctx):
        # TODO gtk3 no mask yet
        #self.gc.set_clip_mask( self.owner.blockMask )
        #self.gc.set_clip_origin( event.area.x - Block.Block.KEYMASK_START, event.area.y )
        # TODO: why is doing this?
        #widget.window.draw_drawable( self.gc, widget.image[widget.get_active()], 0, 0, event.area.x, event.area.y, event.area.width, event.area.height )
        Gtk.ToggleButton.do_draw(self, ctx)
        return True

    def keyToggled( self, widget ):
        if self.ignoreToggle:
            return

        if widget.get_active():
            self.block.setData( "key", widget.key )

            self.ignoreToggle = True

            if self.key != None: # clear old key
                self.GUI[self.key].set_active( False )
                self.key = None

            widget.set_active( False )

            self.ignoreToggle = False

        self.popdown( True )

    def handleNone( self, widget ):
        if self.key != None:
            self.ignoreToggle = True
            self.GUI[self.key].set_active( False )
            self.key = None
            self.ignoreToggle = False

        self.block.setData( "key", None )

        self.popdown( True )
