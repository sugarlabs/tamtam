#import pygtk
import gtk
#import os
#import sets

class ScrolledToolbar(gtk.HBox):
    def __init__(self):
        gtk.HBox.__init__( self )

        scrollLeftImg = gtk.Image()
        scrollLeftImg.set_from_icon_name('go-left', gtk.ICON_SIZE_BUTTON)
        self._scrollLeft = gtk.Button( label = None )
        self._scrollLeft.set_relief(gtk.RELIEF_NONE)
        self._scrollLeft.set_image(scrollLeftImg)
        self._scrollLeft.connect( "clicked", self.doScroll, "left" )
        self.pack_start( self._scrollLeft, False, False )

        self._scrolledWindow = gtk.ScrolledWindow()
        self._scrolledWindow.set_policy( gtk.POLICY_ALWAYS, gtk.POLICY_NEVER )
        self.pack_start( self._scrolledWindow )
        self._hadjustment = self._scrolledWindow.get_hadjustment()
        self._hadjustment.connect( "changed", self.scrollChanged )
        self._hadjustment.connect( "value-changed", self.scrollChanged )

        scrollRightImg = gtk.Image()
        scrollRightImg.set_from_icon_name('go-right', gtk.ICON_SIZE_BUTTON)
        self._scrollRight = gtk.Button( label = None )
        self._scrollRight.set_relief(gtk.RELIEF_NONE)
        self._scrollRight.set_image(scrollRightImg)
        self._scrollRight.connect( "clicked", self.doScroll, "right" )
        self.pack_start( self._scrollRight, False, False )

    def set_viewport(self, widget):
        self._scrolledWindow.add_with_viewport(widget)

    def get_adjustment(self):
        return self._hadjustment

    def doScroll( self, widget, data ):
        if data == "left":
            val = max( self._hadjustment.get_property("lower"), self._hadjustment.get_value() - self._hadjustment.get_property("page_increment") )
        else:
            val = min( self._hadjustment.get_property("upper") - self._hadjustment.get_property("page_size"), self._hadjustment.get_value() + self._hadjustment.get_property("page_increment") )

        self._hadjustment.set_value( val )

    def scrollChanged( self, widget ):
        val = self._hadjustment.get_value()
        if val == 0:
            self._scrollLeft.set_sensitive( False )
        else:
            self._scrollLeft.set_sensitive( True )

        if val >= self._hadjustment.get_property( "upper" ) - self._hadjustment.get_property("page_size"):
            self._scrollRight.set_sensitive( False )
        else:
            self._scrollRight.set_sensitive( True )

    def get_viewport_allocation(self):
        alloc = self._scrolledWindow.get_allocation()
        alloc.x -= self._hadjustment.get_value()
        return alloc
