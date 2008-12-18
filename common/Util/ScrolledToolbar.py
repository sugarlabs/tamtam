import gtk
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.icon import Icon

class ScrollButton(gtk.ToolButton):
    def __init__(self, icon_name):
        gtk.ToolButton.__init__(self)

        icon = Icon(icon_name = icon_name,
                icon_size=gtk.ICON_SIZE_SMALL_TOOLBAR)
        # The alignment is a hack to work around gtk.ToolButton code
        # that sets the icon_size when the icon_widget is a gtk.Image
        alignment = gtk.Alignment(0.5, 0.5)
        alignment.add(icon)
        self.set_icon_widget(alignment)
        
class ScrolledToolbar(gtk.EventBox):
    def __init__(self, arrows_policy = gtk.POLICY_AUTOMATIC):
        gtk.EventBox.__init__(self)
        self._viewport = None
        self._abox = None
        self._aviewport = None
        self._aviewport_sig = None
        self._arrows_policy = arrows_policy
        self._scrollLeft = None
        self._scrollRight = None

        box = gtk.HBox()
        if self._arrows_policy == gtk.POLICY_AUTOMATIC:
            box.connect("size-allocate", self._box_allocate_cb)
        self.add(box)

        if self._arrows_policy != gtk.POLICY_NEVER:
            self._scrollLeft = ScrollButton('go-left')
            self._scrollLeft.props.can_focus = False
            self._scrollLeft.connect( "clicked", self._scroll_cb, "left" )
            box.pack_start(self._scrollLeft, False, False, 0)

        self._scrolledWindow = gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)
        self._scrolledWindow.connect('scroll-event', self._scroll_event_cb)
        box.pack_start(self._scrolledWindow, True, True, 0)
        self._hadjustment = self._scrolledWindow.get_hadjustment()
        self._hadjustment.connect( "changed", self._scroll_changed_cb )
        self._hadjustment.connect( "value-changed", self._scroll_changed_cb )

        if self._arrows_policy != gtk.POLICY_NEVER:
            self._scrollRight = ScrollButton('go-right')
            self._scrollRight.props.can_focus = False
            self._scrollRight.connect( "clicked", self._scroll_cb, "right" )
            box.pack_start(self._scrollRight, False, False, 0)

    def modify_bg(self, state, bg):
        gtk.EventBox.modify_bg(self, state, bg)
        self._viewport.get_parent().modify_bg(state, bg)

    def set_viewport(self, widget):
        if widget == self._viewport: return
        if self._viewport and self._aviewport_sig:
            self._viewport.disconnect(self._aviewport_sig)
        self._viewport = widget

        if self._arrows_policy == gtk.POLICY_AUTOMATIC:
            self._aviewport_sig = self._viewport.connect("size-allocate",
                    self._viewport_allocate_cb)

        self._scrolledWindow.add_with_viewport(widget)

    def get_viewport_allocation(self):
        alloc = self._scrolledWindow.get_allocation()
        alloc.x -= self._hadjustment.get_value()
        return alloc

    def get_adjustment(self):
        return self._hadjustment

    def _box_allocate_cb(self, w, a):
        self._abox = a
        self._update_arrows()

    def _viewport_allocate_cb(self, w, a):
        self._aviewport = a
        self._update_arrows()

    def _update_arrows(self):
        if not self._abox or not self._aviewport: return

        if self._abox.width < self._aviewport.width:
            self._scrollLeft.show()
            self._scrollRight.show()
        else:
            self._scrollLeft.hide()
            self._scrollRight.hide()


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
        if self._scrollLeft:
            if val == 0:
                self._scrollLeft.set_sensitive( False )
            else:
                self._scrollLeft.set_sensitive( True )

        if self._scrollRight:
            if val >= self._hadjustment.get_property( "upper" ) - \
                    self._hadjustment.get_property("page_size"):
                self._scrollRight.set_sensitive( False )
            else:
                self._scrollRight.set_sensitive( True )
