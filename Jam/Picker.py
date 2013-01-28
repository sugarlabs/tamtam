from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

import os
import cairo
import sets
import StringIO

from common.Util.CSoundClient import new_csound_client
from common.port.scrolledbox import HScrolledBox
import common.Config as Config
from common.Util import CairoUtil
from   gettext import gettext as _

from sugar3.graphics.palette import Palette, WidgetInvoker

from common.Util import ControlStream
from common.Util import InstrumentDB

from Jam import Block

class Picker(HScrolledBox):

    def __init__( self, owner, filter = None ):
        HScrolledBox.__init__(self)

        self.owner = owner

        self.colors = owner.colors
        # TODO gtk3 no masks yet
        #self.blockMask = owner.blockMask

        self.filter = filter

        self.desktop = owner.getDesktop()

        self.pickerBox = Gtk.HBox()
        self.set_viewport(self.pickerBox)
        self.modify_bg( Gtk.StateType.NORMAL, self.colors["Picker_Bg"] )

        # spacers
        self.pickerBox.pack_start( Gtk.Label(" "), True, True, 0)
        self.pickerBox.pack_end( Gtk.Label(" "), True, True, 0)

        self.show_all()
        self.scroll = {}
        self.scroll[filter] = 0

        self.blocks = []

    def addBlock( self, data, name, block ):
        # tooltip
        invoker = WidgetInvoker(block)
        invoker._position_hint = WidgetInvoker.AT_CURSOR
        invoker.set_palette(Palette(name))

        block.add_events( Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.ENTER_NOTIFY_MASK
                        | Gdk.EventMask.LEAVE_NOTIFY_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK
                        | Gdk.EventMask.POINTER_MOTION_HINT_MASK )
        block.connect( "button-press-event", self.on_button_press )
        block.connect( "button-release-event", self.on_button_release )
        block.connect( "motion-notify-event", self.on_motion_notify )
        block.data = data

        self.blocks.append( block )

        if self._testAgainstFilter( block ):
            self.pickerBox.pack_start( block, False, False, 3 )

        block.show_all()

        return block

    def getFilter( self ):
        return filter

    def setFilter( self, filter ):
        if filter == self.filter:
            return

        self.scroll[self.filter] = self.get_adjustment().get_value()

        self.filter = filter

        for block in self.pickerBox.get_children()[1:-1]: # outside children are spacers
            self.pickerBox.remove( block )

        for block in self.blocks:
            if self._testAgainstFilter( block ):
                self.pickerBox.pack_start( block, False, False, 3 )

        if self.scroll.has_key( filter ):
            self.get_adjustment().set_value( self.scroll[filter] )
        else:
            self.get_adjustment().set_value( 0 )
            self.scroll[filter] = 0

    def _testAgainstFilter( self, block ):
        return True

    def on_button_press( self, widget, event ):
        pass

    def on_button_release( self, widget, event ):
        self.desktop.on_button_release( widget, event )

    def on_motion_notify( self, widget, event ):
        self.desktop.on_motion_notify( widget, event )


class Instrument( Picker ):

    def __init__( self, owner, filter =  ( "All" ) ):
        Picker.__init__( self, owner, filter )

        self.type = Instrument

        self.instrumentDB = InstrumentDB.getRef()

        all = []
        lab = []
        mic = []
        
        for i in self.instrumentDB.getSet( "All" ):
            if i.name.startswith('lab'):
                lab.append(i)
            elif i.name.startswith('mic'):
                mic.append(i)
            elif not i.kitStage and not i.kit:
                all.append(i)

        all += sorted(lab, key=lambda i: i.name)
        all += sorted(mic, key=lambda i: i.name)

        for inst in all:
            self.addBlock( inst.instrumentId )

    def addBlock( self, id ):
        # match data structure of Block.Instrument
        data = { "name": self.instrumentDB.instId[id].nameTooltip,
                 "id":   id }

        width = Block.Instrument.WIDTH
        height = Block.Instrument.HEIGHT
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        ctx.save()
        ctx.set_line_width(3)
        ctx.set_source_rgb(*CairoUtil.gdk_color_to_cairo(
                self.colors["Bg_Inactive"]))
        CairoUtil.draw_round_rect(ctx, 0, 0, width, width)
        ctx.fill_preserve()

        ctx.set_source_rgb(*CairoUtil.gdk_color_to_cairo(
                self.colors["Border_Inactive"]))
        ctx.stroke()
        ctx.restore()

        # draw block
        ctx.set_source_surface(self.owner.getInstrumentImage(data["id"]), 0, 0)
        ctx.paint()

        # may be there are a better way to put the content of the surface in
        # a GtkImage
        pixbuf_data = StringIO.StringIO()
        surface.write_to_png(pixbuf_data)
        pxb_loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        pxb_loader.write(pixbuf_data.getvalue())
        pxb_loader.close()

        image = Gtk.Image.new_from_pixbuf(pxb_loader.get_pixbuf())

        block = Gtk.EventBox()
        block.modify_bg(Gtk.StateType.NORMAL, self.colors["Picker_Bg"])
        block.add(image)

        Picker.addBlock( self, data, data["name"], block )

    def _testAgainstFilter( self, block ):
        if "All" in self.filter:
            return True

        if self.instrumentDB.getInstrument( block.data["id"] ).category in self.filter:
            return True

        return False

    def on_button_press( self, widget, event ):
        walloc = widget.get_allocation()
        valloc = self.get_viewport_allocation()
        loc = ( valloc.x + walloc.x + event.x, -1 )

        block = self.desktop.addBlock( Block.Instrument, widget.data, loc, True )
        self.desktop.activateInstrument( block )


class Drum( Picker ):

    def __init__( self, owner, filter = None ):
        Picker.__init__( self, owner, filter )

        self.type = Drum

        self.instrumentDB = InstrumentDB.getRef()

        for inst in self.instrumentDB.getSet( "percussions" ):
            if self.instrumentDB.instNamed[inst.name].kit:
                self.addBlock( inst.instrumentId )

    def addBlock( self, id ):
        # match data structure of Block.Drum
        data = { "name":       self.instrumentDB.instId[id].nameTooltip,
                 "id":         id }

        width = Block.Drum.WIDTH
        height = Block.Drum.HEIGHT

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        ctx.save()
        ctx.set_line_width(3)
        ctx.set_source_rgb(*CairoUtil.gdk_color_to_cairo(
                self.colors["Bg_Inactive"]))
        CairoUtil.draw_drum_mask(ctx, 0, 0, width)
        ctx.fill_preserve()

        ctx.set_source_rgb(*CairoUtil.gdk_color_to_cairo(
                self.colors["Border_Inactive"]))
        ctx.stroke()
        ctx.restore()

        # draw block
        ctx.set_source_surface(self.owner.getInstrumentImage(data["id"]), 0, 0)
        ctx.paint()

        # may be there are a better way to put the content of the surface in
        # a GtkImage
        pixbuf_data = StringIO.StringIO()
        surface.write_to_png(pixbuf_data)
        pxb_loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        pxb_loader.write(pixbuf_data.getvalue())
        pxb_loader.close()

        image = Gtk.Image.new_from_pixbuf(pxb_loader.get_pixbuf())

        block = Gtk.EventBox()
        block.modify_bg(Gtk.StateType.NORMAL, self.colors["Picker_Bg"])
        block.add(image)

        Picker.addBlock( self, data, data["name"], block )

    def on_button_press( self, widget, event ):
        walloc = widget.get_allocation()
        valloc = self.get_viewport_allocation()
        loc = ( valloc.x + walloc.x + event.x, -1 )
        self.desktop.addBlock( Block.Drum, widget.data, loc, True )


class Loop( Picker ):

    def __init__( self, owner, filter = None ):
        Picker.__init__( self, owner, filter )

        self.type = Loop

        self.presetLoops = self._scanDirectory( Config.FILES_DIR+"/Loops" )

    def _loadFile( self, fullpath, filename ):
        if filename[-4:] != ".ttl":
            if Config.DEBUG >= 3: print "WARNING: incorrect extension on loop file: " + filename
            return -1
        try:
            oldPages = sets.Set( self.owner.noteDB.getTune() )

            ifile = open( fullpath, 'r' )
            ttt = ControlStream.TamTamTable ( self.owner.noteDB )
            ttt.parseFile( ifile )
            ifile.close()

            curPages = sets.Set( self.owner.noteDB.getTune() )
            newPages = curPages.difference( oldPages )

            if len(newPages) != 1:
                print "ERROR: bad loop file, contains more than one page (or none)"
                return -1

            id = newPages.pop() # new pageId

            self.owner.noteDB.getPage( id ).setLocal( False ) # flag as a global page

            self.addBlock( id, filename[:-4] )

            return id

        except OSError,e:
            print 'ERROR: failed to open file %s for reading\n' % ofilename
            return -1

    def _scanDirectory( self, path ):
        dirlist = os.listdir( path )
        ids = []
        for fpath in dirlist:
            id = self._loadFile( path+"/"+fpath, fpath )
            if id != -1: ids.append(id)
        return ids

    def addBlock( self, id, name ):
        # match data structure of Block.Loop
        data = { "name": _('Loop'),
                 "id":   id }

        self.owner.updateLoopImage( data["id"] )
        loop = self.owner.getLoopImage( data["id"] )

        page = self.owner.noteDB.getPage(id)

        width = Block.Loop.WIDTH[page.beats]
        height = Block.Loop.HEIGHT

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        # draw bg
        ctx.save()
        ctx.set_line_width(3)
        ctx.set_source_rgb(*CairoUtil.gdk_color_to_cairo(
                self.colors["Bg_Inactive"]))
        CairoUtil.draw_loop_mask(ctx, 0, 0, width, height)
        ctx.fill_preserve()

        ctx.set_source_rgb(*CairoUtil.gdk_color_to_cairo(
                self.colors["Border_Inactive"]))
        ctx.stroke()
        ctx.restore()

        # draw block
        ctx.set_source_surface(loop)
        ctx.paint()

        # may be there are a better way to put the content of the surface in
        # a GtkImage
        pixbuf_data = StringIO.StringIO()
        surface.write_to_png(pixbuf_data)
        pxb_loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        pxb_loader.write(pixbuf_data.getvalue())
        pxb_loader.close()

        image = Gtk.Image.new_from_pixbuf(pxb_loader.get_pixbuf())

        block = Gtk.EventBox()
        block.modify_bg( Gtk.StateType.NORMAL, self.colors["Picker_Bg"] )
        block.add( image )

        Picker.addBlock( self, data, data["name"], block )

    def on_button_press( self, widget, event ):
        walloc = widget.get_allocation()
        valloc = self.get_viewport_allocation()
        loc = ( valloc.x + walloc.x + event.x, -1 )

        data = {}
        for key in widget.data.keys():
            data[key] = widget.data[key]

        newid = self.owner.noteDB.duplicatePages( [ data["id"] ] )[data["id"]]
        self.owner.updateLoopImage( newid )
        data["id"] = newid

        block = self.desktop.addBlock( Block.Loop, data, loc, True )
