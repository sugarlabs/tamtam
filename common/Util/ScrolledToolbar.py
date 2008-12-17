import gtk
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.icon import Icon

class ScrollButton(gtk.ToolButton):
    def __init__(self, icon_name):
        gtk.ToolButton.__init__(self)

        icon = Icon(icon_name = icon_name, icon_size=gtk.ICON_SIZE_SMALL_TOOLBAR)
        # The alignment is a hack to work around gtk.ToolButton code
        # that sets the icon_size when the icon_widget is a gtk.Image
        alignment = gtk.Alignment(0.5, 0.5)
        alignment.add(icon)
        self.set_icon_widget(alignment)
        
class ScrolledToolbar(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)

        box = gtk.HBox()
        self.add(box)

        self._scrollLeft = ScrollButton('go-left')
        self._scrollLeft.connect( "clicked", self._scroll_cb, "left" )
        box.pack_start( self._scrollLeft, False, False )

        self._scrolledWindow = gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_NEVER)
        self._scrolledWindow.connect('scroll-event', self._scroll_event_cb)
        box.pack_start( self._scrolledWindow )
        self._hadjustment = self._scrolledWindow.get_hadjustment()
        self._hadjustment.connect( "changed", self._scroll_changed_cb )
        self._hadjustment.connect( "value-changed", self._scroll_changed_cb )

        self._scrollRight = ScrollButton('go-right')
        self._scrollRight.connect( "clicked", self._scroll_cb, "right" )
        box.pack_start(self._scrollRight, False, False)

    def modify_bg(self, state, bg):
        gtk.EventBox.modify_bg(self, state, bg)
        self._viewport.get_parent().modify_bg(state, bg)

    def set_viewport(self, widget):
        self._viewport = widget
        self._scrolledWindow.add_with_viewport(widget)

    def get_viewport_allocation(self):
        alloc = self._scrolledWindow.get_allocation()
        alloc.x -= self._hadjustment.get_value()
        return alloc

    def get_adjustment(self):
        return self._hadjustment

    def _scroll_event_cb(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_UP: event.direction = gtk.gdk.SCROLL_LEFT
        if event.direction == gtk.gdk.SCROLL_DOWN: event.direction = gtk.gdk.SCROLL_RIGHT
        return False

    def _scroll_cb( self, widget, data ):
        if data == "left":
            val = max( self._hadjustment.get_property("lower"), self._hadjustment.get_value() - self._hadjustment.get_property("page_increment") )
        else:
            val = min( self._hadjustment.get_property("upper") - self._hadjustment.get_property("page_size"), self._hadjustment.get_value() + self._hadjustment.get_property("page_increment") )

        self._hadjustment.set_value( val )

    def _scroll_changed_cb( self, widget ):
        val = self._hadjustment.get_value()
        if val == 0:
            self._scrollLeft.set_sensitive( False )
        else:
            self._scrollLeft.set_sensitive( True )

        if val >= self._hadjustment.get_property( "upper" ) - self._hadjustment.get_property("page_size"):
            self._scrollRight.set_sensitive( False )
        else:
            self._scrollRight.set_sensitive( True )
