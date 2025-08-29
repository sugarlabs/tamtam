from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo
import math

import logging
import common.Config as Config
from common.Config import imagefile
from common.Util import CairoUtil

from sugar3.graphics.combobox import ComboBox
from sugar3.graphics.palette import Palette, WidgetInvoker


class ImageVScale(Gtk.VScale):

    def __init__(self, image_name, adjustment=None, slider_border=0,
            insensitive_name=None, trough_color="#3D403A", snap=False):

        image_name = imagefile(image_name)

        Gtk.VScale.__init__(self)
        self.set_adjustment(adjustment)

        if snap:
            self.snap = 1 / snap
        else:
            self.snap = False

        img = Gtk.Image()
        img.set_from_file(image_name)
        self.sliderPixbuf = img.get_pixbuf()

        if insensitive_name == None:
            self.insensitivePixbuf = None
        else:
            img = Gtk.Image()
            img.set_from_file(insensitive_name)
            self.insensitivePixbuf = img.get_pixbuf()

        name = image_name + "ImageVScale"
        self.set_name(name)

        self.pixbufWidth = self.sliderPixbuf.get_width()
        self.pixbufHeight = self.sliderPixbuf.get_height()
        self.sliderBorder = slider_border

        self.set_draw_value(False)

        self.connect("draw", self.__draw_cb)
        self.connect("button-release-event", self.button_release)
        adjustment.connect("value-changed", self.value_changed)

    def set_snap(self, snap):
        if snap:
            self.snap = 1 / snap
        else:
            self.snap = False
        self.queue_draw()

    def value_changed(self, adjustment):
        if self.snap:
            val = round(self.snap * self.get_value()) / self.snap
            if val != self.get_value():
                self.set_value(val)

    def __draw_cb(self, widget, ctx):

        ctx.save()
        ctx.set_source_rgb(0, 0, 0)
        alloc = self.get_allocation()
        ctx.rectangle(alloc.width // 2 - self.sliderBorder - 1,
                self.sliderBorder, 2,
                alloc.height - self.sliderBorder * 2)
        ctx.fill()
        ctx.restore()

        val = self.get_value()
        if self.snap:
            val = round(self.snap * val) / self.snap
        adj = self.get_adjustment()

        if self.get_inverted():
            sliderY = int((alloc.height - self.pixbufHeight) * \
                (adj.get_upper() - val) / (adj.get_upper() - adj.get_lower()))
        else:
            sliderY = int((alloc.height - self.pixbufHeight) * \
                val / (adj.get_upper() - adj.get_lower()))

        ctx.save()
        ctx.translate(0, sliderY)
        if self.insensitivePixbuf != None and \
                self.state == Gtk.StateType.INSENSITIVE:
            Gdk.cairo_set_source_pixbuf(ctx, self.insensitivePixbuf, 0, 0)
            ctx.paint()
        else:
            Gdk.cairo_set_source_pixbuf(ctx, self.sliderPixbuf, 0, 0)
            ctx.paint()

        ctx.restore()
        return True

    def button_release(self, widget, event):

        if self.snap:
            self.set_value(round(self.snap * self.get_value()) / self.snap)


class XYSlider(Gtk.EventBox):

    def __init__(self, fixed, button, xadjustment, yadjustment, flipX=False,
            flipY=False):
        Gtk.EventBox.__init__(self)

        self.fixed = fixed
        self.button = button
        self.xadjustment = xadjustment
        self.yadjustment = yadjustment
        self.flipX = flipX
        self.flipY = flipY

        if button.get_parent() is None:
            fixed.put(button, 0, 0)

        self.add(fixed)

        self.fWidth = self.fHeight = 1
        self.bWidth = self.bHeight = 1

        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.connect("size-allocate", lambda w, a: self.updateAlloc())
        self.connect("button-press-event", self.handlePress)
        self.connect("button-release-event", self.handleRelease)
        self.connect("motion-notify-event", self.handleMotion)
        self.button.connect("size-allocate", lambda w, a: self.updateButton())
        self.button.connect("button-press-event", self.handleButtonPress)
        self.button.connect("button-release-event", self.handleButtonRelease)
        self.button.add_events(Gdk.EventMask.BUTTON_MOTION_MASK |
                Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.button.connect("motion-notify-event", self.handleMotion)
        
        self.xadjustment.connect("changed",
                lambda a1: self.updateAdjustment("x"))
        self.xadjustment.connect("value-changed", lambda a1: self.updateLoc())
        self.yadjustment.connect("changed",
                lambda a1: self.updateAdjustment("y"))
        self.yadjustment.connect("value-changed",
                lambda a1: self.updateLoc())

        self.updateAdjustment("x")
        self.updateAdjustment("y")
        self.updateButton()

    def updateAlloc(self):
        alloc = self.fixed.get_allocation()
        if self.fWidth != alloc.width or self.fHeight != alloc.height:
            self.fWidth = alloc.width
            self.fHeight = alloc.height
            self.width = self.fWidth - self.bWidth
            self.height = self.fHeight - self.bHeight
            self.updateLoc()

    def updateButton(self):
        alloc = self.button.get_allocation()
        if self.bWidth != alloc.width or self.bHeight != alloc.height:
            self.bWidth = alloc.width
            self.bHeight = alloc.height
            self.bWidthDIV2 = alloc.width // 2
            self.bHeightDIV2 = alloc.height // 2
            self.width = self.fWidth - self.bWidth
            self.height = self.fHeight - self.bHeight
            self.updateLoc()

    def updateAdjustment(self, which):
        if which == "x":
            self.xRange = int(self.xadjustment.upper - self.xadjustment.lower)
        else:
            self.yRange = int(self.yadjustment.upper - self.yadjustment.lower)

    def updateLoc(self):
        if self.flipX:
            self.x = (self.width * int(self.xadjustment.upper -
                    self.xadjustment.value)) // self.xRange
        else:
            self.x = (self.width * int(self.xadjustment.value -
                    self.xadjustment.lower)) // self.xRange
        if self.flipY:
            self.y = (self.height * int(self.yadjustment.upper -
                    self.yadjustment.value)) // self.yRange
        else:
            self.y = (self.height * int(self.yadjustment.value -
                    self.yadjustment.lower)) // self.yRange

        self.fixed.move(self.button, self.x, self.y)

    def handlePress(self, w, event):
        self.clickOffset = (0, 0)
        self.updatePointer(int(event.x), int(event.y))
        self.button.set_active(True)

    def handleRelease(self, w, event):
        self.button.set_active(False)
        return True

    def handleButtonPress(self, w, event):
        self.clickOffset = (event.x - self.bWidthDIV2,
                event.y - self.bHeightDIV2)
        self.button.set_active(True)

    def handleButtonRelease(self, w, event):
        self.button.set_active(False)
        return True  # block event propagation

    def handleMotion(self, w, event):
        # Get pointer position relative to the widget
        window = self.get_window()
        if window is None:
            return False
            
        # Get device position (x, y) in window coordinates
        success, x, y, mask = window.get_device_position(event.get_device())
        if not success:
            return False
            
        # Convert to widget coordinates
        x, y = self.translate_coordinates(w, x, y)
        if x is None or y is None:
            return False
            
        self.updatePointer(int(x - self.clickOffset[0]),
                int(y - self.clickOffset[1]))
        return True

    def updatePointer(self, x, y):
        x -= self.bWidthDIV2
        y -= self.bHeightDIV2
        if x < 0:
            x = 0
        elif x > self.width:
            x = self.width
        if y < 0:
            y = 0
        elif y > self.height:
            y = self.height
        if self.flipX:
            xvalue = self.xadjustment.lower + \
                    (self.xRange * (self.width - x)) // self.width
        else:
            xvalue = self.xadjustment.lower + (self.xRange * x) // self.width
        if xvalue != self.xadjustment.value:
            self.xadjustment.set_value(xvalue)
        if self.flipY:
            yvalue = self.yadjustment.lower + (self.yRange * \
                    (self.height - y)) // self.height
        else:
            yvalue = self.yadjustment.lower + (self.yRange * y) // self.height
        if yvalue != self.yadjustment.value:
            self.yadjustment.set_value(yvalue)


class RoundHBox(Gtk.HBox):

    def __init__(self, radius=5, fillcolor="#000000", bordercolor="#FFFFFF",
            homogeneous=False, spacing=0):
        Gtk.HBox.__init__(self, homogeneous=homogeneous, spacing=spacing)
        self.alloc = None

        self.radius = radius
        
        # Store colors as Gdk.RGBA for GTK3
        self.fillcolor = Gdk.RGBA()
        self.fillcolor.parse(fillcolor)
        self.bordercolor = Gdk.RGBA()
        self.bordercolor.parse(bordercolor)
        
        self.border_width = 1  # Default border width

        self.connect("draw", self.on_draw)
        self.connect("size-allocate", self.on_size_allocate)

    def update_constants(self):
        if self.alloc is None:
            return
            
        self.borderW = self.get_border_width()
        self.borderWMUL2 = self.borderW * 2
        self.corner = self.radius + self.borderW
        self.cornerMUL2 = self.corner * 2
        self.cornerMINborderW = self.corner - self.borderW
        
        # In GTK3, allocation is already in widget coordinates
        self.widthMINborderW = self.alloc.width - self.borderW
        self.widthMINcorner = self.alloc.width - self.corner
        self.widthMINcornerMUL2 = self.alloc.width - self.cornerMUL2
        self.heightMINborderW = self.alloc.height - self.borderW
        self.heightMINcorner = self.alloc.height - self.corner
        self.heightMINborderWMUL2 = self.alloc.height - self.borderWMUL2
        self.heightMINcornerMUL2 = self.alloc.height - self.cornerMUL2
        
        # For drawing rounded rectangles
        self.roundD = self.radius * 2
        self.rightAngle = 90 * 64

    def size_allocate(self, widget, allocation):
        self.alloc = allocation
        self.update_constants()
        return False

    def set_border_width(self, width):
        Gtk.HBox.set_border_width(self, width)
        self.border_width = width
        self.queue_draw()

    def set_radius(self, radius):
        self.radius = radius
        self.queue_draw()

    def set_fill_color(self, color):
        self.fillcolor = Gdk.RGBA()
        self.fillcolor.parse(color)
        self.queue_draw()

    def set_border_color(self, color):
        self.bordercolor = Gdk.RGBA()
        self.bordercolor.parse(color)
        self.queue_draw()

    def on_draw(self, widget, cr):
        if self.alloc is None:
            return False
            
        # Get the style context for theming
        style = self.get_style_context()
        
        # Draw the background with rounded corners
        Gtk.render_background(
            style, cr, 0, 0,
            self.alloc.width, self.alloc.height
        )
        
        # Draw the filled area with rounded corners
        cr.set_source_rgba(
            self.fillcolor.red,
            self.fillcolor.green,
            self.fillcolor.blue,
            self.fillcolor.alpha
        )
        
        # Draw rounded rectangle
        x, y = 0, 0
        width, height = self.alloc.width, self.alloc.height
        radius = self.radius
        
        cr.new_sub_path()
        cr.arc(x + width - radius, y + radius, radius, -math.pi/2, 0)
        cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi/2)
        cr.arc(x + radius, y + height - radius, radius, math.pi/2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.fill()
        
        # Draw border
        cr.set_source_rgba(
            self.bordercolor.red,
            self.bordercolor.green,
            self.bordercolor.blue,
            self.bordercolor.alpha
        )
        cr.set_line_width(self.border_width)
        cr.stroke()
        
        # Let the default handler draw the children
        return False

        style = self.get_style()

        event = widget.get_allocation()
        startX = event.x - self.alloc.x
        startY = event.y - self.alloc.y
        stopX = startX + event.width
        stopY = startY + event.height

        # Note: could maybe do some optimization to fill only areas that are
        # within the dirty rect, but drawing seems to be quite fast compared
        # to python code, so just leave it at clipping by each geometry feature

        b = self.bordercolor
        cr.set_source_rgb(b.red / 65536.0, b.green / 65536.0, b.blue / 65536.0)
        if self.borderW:
            if stopY > self.corner and startY < self.heightMINcorner:
                if startX < self.borderW:         # draw left border
                    cr.rectangle(self.alloc.x, self.yPLUcorner, self.borderW,
                            self.heightMINcornerMUL2)
                if stopX > self.widthMINborderW:  # draw right border
                    cr.rectangle(self.xPLUwidthMINborderW, self.yPLUcorner,
                            self.borderW, self.heightMINcornerMUL2)

            if stopX > self.corner and startX < self.widthMINcorner:
                if startY < self.borderW:         # draw top border
                    cr.rectangle(self.xPLUcorner, self.alloc.y,
                            self.widthMINcornerMUL2, self.borderW)
                if stopY > self.heightMINborderW:  # draw bottom border
                    cr.rectangle(self.xPLUcorner, self.yPLUheightMINborderW,
                            self.widthMINcornerMUL2, self.borderW)

        if startX < self.corner:
            if startY < self.corner:              # draw top left corner
                cr.rectangle(self.alloc.x, self.alloc.y, self.corner,
                        self.corner)
                cr.fill()
                f = self.fillcolor
                cr.set_source_rgb(f.red / 65536.0, f.green / 65536.0,
                        f.blue / 65536.0)
                #cr.arc( self.roundX1, self.roundY1, self.roundD, self.roundD,
                #self.rightAngle, self.rightAngle )
                #cr.fill()
                cr.set_source_rgb(b.red / 65536.0, b.green / 65536.0,
                        b.blue / 65536.0)

            if stopY > self.heightMINcorner:      # draw bottom left corner
                cr.rectangle(self.alloc.x, self.yPLUheightMINcorner,
                        self.corner, self.corner)
                cr.fill()
                f = self.fillcolor
                cr.set_source_rgb(f.red / 65536.0, f.green / 65536.0,
                        f.blue / 65536.0)
                #cr.arc(self.roundX1, self.roundY2, self.roundD, self.roundD,
                #-self.rightAngle, -self.rightAngle )
                #cr.fill()
                b = self.bordercolor
                cr.set_source_rgb(b.red / 65536.0, b.green / 65536.0,
                        b.blue / 65536.0)

        if stopX > self.widthMINcorner:
            if startY < self.corner:              # draw top right corner
                cr.rectangle(self.xPLUwidthMINcorner, self.alloc.y,
                        self.corner, self.corner)
                cr.fill()
                f = self.fillcolor
                cr.set_source_rgb(f.red / 65536.0, f.green / 65536.0,
                        f.blue / 65536.0)
                #cr.arc(self.roundX2, self.roundY1, self.roundD, self.roundD,
                # 0, self.rightAngle)
                #cr.fill()
                b = self.bordercolor
                cr.set_source_rgb(b.red / 65536.0, b.green / 65536.0,
                        b.blue / 65536.0)

            if stopY > self.heightMINcorner:      # draw bottom right corner
                cr.rectangle(self.xPLUwidthMINcorner, self.yPLUheightMINcorner,
                        self.corner, self.corner)
                cr.fill()
                f = self.fillcolor
                cr.set_source_rgb(f.red / 65536.0, f.green / 65536.0,
                        f.blue / 65536.0)
                #cr.arc(self.roundX2, self.roundY2, self.roundD, self.roundD,
                # 0, -self.rightAngle)
                #cr.fill()
                b = self.bordercolor
                cr.set_source_rgb(b.red / 65536.0, b.green / 65536.0,
                        b.blue / 65536.0)

        f = self.fillcolor
        cr.set_source_rgb(f.red / 65536.0, f.green / 65536.0, f.blue / 65536.0)

        if startX < self.widthMINcorner and stopX > self.corner:
            # draw centre fill
            if startY < self.heightMINborderW and stopY > self.borderW:
                cr.rectangle(self.xPLUcorner, self.yPLUborderW,
                        self.widthMINcornerMUL2, self.heightMINborderWMUL2)
                cr.fill()
        if startX < self.corner and stopX > self.borderW:
            # draw left fill
            if startY < self.heightMINcorner and stopY > self.corner:
                cr.rectangle(self.xPLUborderW, self.yPLUcorner,
                        self.cornerMINborderW, self.heightMINcornerMUL2)
                cr.fill()
        if startX < self.widthMINborderW and stopX > self.widthMINcorner:
            # draw right fill
            if startY < self.heightMINcorner and stopY > self.corner:
                cr.rectangle(self.xPLUwidthMINcorner, self.yPLUcorner,
                        self.cornerMINborderW, self.heightMINcornerMUL2)
                cr.fill()

        return False


class RoundVBox(Gtk.VBox):

    def __init__(self, radius=5, fillcolor="#000000", bordercolor="#FFFFFF",
                homogeneous=False, spacing=0):
        Gtk.VBox.__init__(self, homogeneous=homogeneous, spacing=spacing)
        self.alloc = None

        self.radius = radius
        
        # Store colors as Gdk.RGBA for GTK3
        self.fillcolor = Gdk.RGBA()
        self.fillcolor.parse(fillcolor)
        self.bordercolor = Gdk.RGBA()
        self.bordercolor.parse(bordercolor)
        
        self.border_width = 1  # Default border width

        self.connect("draw", self.on_draw)
        self.connect("size-allocate", self.on_size_allocate)

    def update_constants(self):
        if self.alloc is None:
            return
            
        self.borderW = self.get_border_width()
        self.borderWMUL2 = self.borderW * 2
        self.corner = self.radius + self.borderW
        self.cornerMUL2 = self.corner * 2
        self.cornerMINborderW = self.corner - self.borderW
        
        # In GTK3, we use relative coordinates (0,0 is top-left of widget)
        self.xPLUborderW = self.borderW
        self.xPLUcorner = self.corner
        self.xPLUwidthMINborderW = self.alloc.width - self.borderW
        self.xPLUwidthMINcorner = self.alloc.width - self.corner
        
        self.yPLUborderW = self.borderW
        self.yPLUcorner = self.corner
        self.yPLUheightMINborderW = self.alloc.height - self.borderW
        self.yPLUheightMINcorner = self.alloc.height - self.corner
        
        self.widthMINborderW = self.alloc.width - self.borderW
        self.widthMINcorner = self.alloc.width - self.corner
        self.widthMINcornerMUL2 = self.alloc.width - self.cornerMUL2
        self.heightMINborderW = self.alloc.height - self.borderW
        self.heightMINcorner = self.alloc.height - self.corner
        self.heightMINborderWMUL2 = self.alloc.height - self.borderWMUL2
        self.heightMINcornerMUL2 = self.alloc.height - self.cornerMUL2
        
        # For drawing rounded rectangles
        self.roundX1 = self.borderW - 1
        self.roundX2 = self.alloc.width - self.corner - self.radius - 1
        self.roundY1 = self.borderW - 1
        self.roundY2 = self.alloc.height - self.corner - self.radius - 1
        self.roundD = self.radius * 2 + 1
        self.rightAngle = 90 * 64

    def on_size_allocate(self, widget, allocation):
        # In GTK3, we need to chain up to the parent's size_allocate
        Gtk.VBox.do_size_allocate(self, allocation)
        self.alloc = allocation
        self.update_constants()
        self.queue_draw()  # Request a redraw when size changes
        return False
        
    def on_draw(self, widget, cr):
        if self.alloc is None:
            return False
            
        # Set up the drawing context
        Gtk.render_background(
            self.get_style_context(),
            cr,
            0, 0,
            self.alloc.width, self.alloc.height
        )
        
        # Set the fill color
        cr.set_source_rgba(
            self.fillcolor.red,
            self.fillcolor.green,
            self.fillcolor.blue,
            self.fillcolor.alpha
        )
        
        # Draw the rounded rectangle using Cairo
        radius = self.radius
        x, y, width, height = 0, 0, self.alloc.width, self.alloc.height
        
        cr.new_sub_path()
        cr.arc(x + width - radius, y + radius, radius, -math.pi/2, 0)
        cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi/2)
        cr.arc(x + radius, y + height - radius, radius, math.pi/2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.fill()
        
        # Draw the border
        cr.set_source_rgba(
            self.bordercolor.red,
            self.bordercolor.green,
            self.bordercolor.blue,
            self.bordercolor.alpha
        )
        cr.set_line_width(self.border_width)
        
        # Draw the border path
        cr.new_sub_path()
        cr.arc(x + width - radius, y + radius, radius, -math.pi/2, 0)
        cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi/2)
        cr.arc(x + radius, y + height - radius, radius, math.pi/2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3*math.pi/2)
        cr.close_path()
        cr.stroke()
        
        # Propagate the draw signal to child widgets
        return False

    def set_border_width(self, width):
        Gtk.VBox.set_border_width(self, width)
        self.update_constants()

    def set_radius(self, radius):
        self.radius = radius
        self.update_constants()

    def set_fill_color(self, color):
        colormap = self.get_colormap()
        self.fillcolor = colormap.alloc_color(color, True, True)

    def set_border_color(self, color):
        colormap = self.get_colormap()
        self.bordercolor = colormap.alloc_color(color, True, True)

    def __draw_cb(self, widget, ctx):

        if self.get_allocation() is None:
            return
        Gtk.VBox.do_draw(self, ctx)
        return True

        # TODO
        style = self.get_style()
        gc = style.fg_gc[gtk.STATE_NORMAL]

        startX = event.area.x - self.alloc.x
        startY = event.area.y - self.alloc.y
        stopX = startX + event.area.width
        stopY = startY + event.area.height

        saveForeground = gc.foreground

        # Note: could maybe do some optimization to fill only areas that are
        # within the dirty rect, but drawing seems to be quite fast compared
        # to python code, so just leave it at clipping by each geometry feature

        gc.foreground = self.bordercolor
        if self.borderW:
            if stopY > self.corner and startY < self.heightMINcorner:
                if startX < self.borderW:         # draw left border
                    self.window.draw_rectangle(gc, True, self.alloc.x,
                            self.yPLUcorner, self.borderW,
                            self.heightMINcornerMUL2)
                if stopX > self.widthMINborderW:  # draw right border
                    self.window.draw_rectangle(gc, True,
                            self.xPLUwidthMINborderW, self.yPLUcorner,
                            self.borderW, self.heightMINcornerMUL2)

            if stopX > self.corner and startX < self.widthMINcorner:
                if startY < self.borderW:         # draw top border
                    self.window.draw_rectangle(gc, True, self.xPLUcorner,
                            self.alloc.y, self.widthMINcornerMUL2,
                            self.borderW)
                if stopY > self.heightMINborderW:  # draw bottom border
                    self.window.draw_rectangle(gc, True, self.xPLUcorner,
                            self.yPLUheightMINborderW,
                            self.widthMINcornerMUL2, self.borderW)

        if startX < self.corner:
            if startY < self.corner:              # draw top left corner
                self.window.draw_rectangle(gc, True, self.alloc.x,
                        self.alloc.y, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX1, self.roundY1,
                        self.roundD, self.roundD, self.rightAngle,
                        self.rightAngle)
                gc.foreground = self.bordercolor
            if stopY > self.heightMINcorner:      # draw bottom left corner
                self.window.draw_rectangle(gc, True, self.alloc.x,
                        self.yPLUheightMINcorner, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX1, self.roundY2,
                        self.roundD, self.roundD, -self.rightAngle,
                        -self.rightAngle)
                gc.foreground = self.bordercolor
        if stopX > self.widthMINcorner:
            if startY < self.corner:              # draw top right corner
                self.window.draw_rectangle(gc, True, self.xPLUwidthMINcorner,
                        self.alloc.y, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX2, self.roundY1,
                        self.roundD, self.roundD, 0, self.rightAngle)
                gc.foreground = self.bordercolor
            if stopY > self.heightMINcorner:      # draw bottom right corner
                self.window.draw_rectangle(gc, True, self.xPLUwidthMINcorner,
                        self.yPLUheightMINcorner, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX2, self.roundY2,
                        self.roundD, self.roundD, 0, -self.rightAngle)
                gc.foreground = self.bordercolor

        gc.foreground = self.fillcolor
        if startX < self.widthMINcorner and stopX > self.corner:
            # draw centre fill
            if startY < self.heightMINborderW and stopY > self.borderW:
                self.window.draw_rectangle(gc, True, self.xPLUcorner,
                        self.yPLUborderW, self.widthMINcornerMUL2,
                        self.heightMINborderWMUL2)
        if startX < self.corner and stopX > self.borderW:
            # draw left fill
            if startY < self.heightMINcorner and stopY > self.corner:
                self.window.draw_rectangle(gc, True, self.xPLUborderW,
                        self.yPLUcorner, self.cornerMINborderW,
                        self.heightMINcornerMUL2)
        if startX < self.widthMINborderW and stopX > self.widthMINcorner:
            # draw right fill
            if startY < self.heightMINcorner and stopY > self.corner:
                self.window.draw_rectangle(gc, True, self.xPLUwidthMINcorner,
                        self.yPLUcorner, self.cornerMINborderW,
                        self.heightMINcornerMUL2)

        gc.foreground = saveForeground

        return False


class RoundFixed(Gtk.Fixed):

    def __init__(self, radius=5, fillcolor="#000", bordercolor="#FFF"):
        Gtk.Fixed.__init__(self)
        self.alloc = None

        self.radius = radius

        self.fillcolor = Gdk.Color.parse(fillcolor)
        self.bordercolor = Gdk.Color.parse(bordercolor)

        self.connect("draw", self.draw)
        self.connect("size-allocate", self.size_allocate)

    def update_constants(self):

        if self.alloc is None:
            return

        self.borderW = self.get_border_width()
        self.borderWMUL2 = self.borderW * 2
        self.corner = self.radius + self.borderW
        self.cornerMUL2 = self.corner * 2
        self.cornerMINborderW = self.corner - self.borderW

        self.xPLUborderW = self.alloc.x + self.borderW
        self.xPLUcorner = self.alloc.x + self.corner
        self.xPLUwidthMINborderW = self.alloc.x + self.alloc.width - \
                self.borderW
        self.xPLUwidthMINcorner = self.alloc.x + self.alloc.width - self.corner
        self.yPLUborderW = self.alloc.y + self.borderW
        self.yPLUcorner = self.alloc.y + self.corner
        self.yPLUheightMINborderW = self.alloc.y + self.alloc.height - \
                self.borderW
        self.yPLUheightMINcorner = self.alloc.y + self.alloc.height - \
                self.corner
        self.widthMINborderW = self.alloc.width - self.borderW
        self.widthMINcorner = self.alloc.width - self.corner
        self.widthMINcornerMUL2 = self.alloc.width - self.cornerMUL2
        self.heightMINborderW = self.alloc.height - self.borderW
        self.heightMINcorner = self.alloc.height - self.corner
        self.heightMINborderWMUL2 = self.alloc.height - self.borderWMUL2
        self.heightMINcornerMUL2 = self.alloc.height - self.cornerMUL2

        self.roundX1 = self.alloc.x + self.borderW - 1
        self.roundX2 = self.alloc.x + self.alloc.width - self.corner - \
                self.radius - 1
        self.roundY1 = self.alloc.y + self.borderW - 1
        self.roundY2 = self.alloc.y + self.alloc.height - self.corner - \
                self.radius - 1
        self.roundD = self.radius * 2 + 1
        self.rightAngle = 90 * 64

    def size_allocate(self, widget, allocation):
        self.alloc = allocation
        self.update_constants()
        return False

    def set_border_width(self, width):
        Gtk.Fixed.set_border_width(self, width)
        self.update_constants()

    def set_radius(self, radius):
        self.radius = radius
        self.update_constants()

    def set_fill_color(self, color):
        self.fillcolor = Gdk.Color.parse(color)

    def set_border_color(self, color):
        self.bordercolor = Gdk.Color.parse(color)

    def draw(self, widget, cr):

        if self.alloc == None:
            return

        area = widget.get_allocation()
        startX = area.x - self.alloc.x
        startY = area.y - self.alloc.y
        stopX = startX + area.width
        stopY = startY + area.height

        #saveForeground = gc.foreground

        # Note: could maybe do some optimization to fill only areas that are
        # within the dirty rect, but drawing seems to be quite fast compared
        # to python code, so just leave it at clipping by each geometry feature

        cr.set_source_rgb(*CairoUtil.gdk_color_to_cairo(self.bordercolor))
        if self.borderW:
            if stopY > self.corner and startY < self.heightMINcorner:
                if startX < self.borderW:         # draw left border
                    cr.rectangle(self.alloc.x, self.yPLUcorner, self.borderW,
                            self.heightMINcornerMUL2)
                    cr.fill()
                if stopX > self.widthMINborderW:  # draw right border
                    cr.rectangle(self.xPLUwidthMINborderW, self.yPLUcorner,
                            self.borderW, self.heightMINcornerMUL2)
                    cr.fill()

            if stopX > self.corner and startX < self.widthMINcorner:
                if startY < self.borderW:         # draw top border
                    cr.rectangle(self.xPLUcorner, self.alloc.y,
                            self.widthMINcornerMUL2, self.borderW)
                    cr.fill()
                if stopY > self.heightMINborderW:  # draw bottom border
                    cr.rectangle(self.xPLUcorner, self.yPLUheightMINborderW,
                            self.widthMINcornerMUL2, self.borderW)
                    cr.fill()

        if startX < self.corner:
            if startY < self.corner:              # draw top left corner
                cr.rectangle(self.alloc.x, self.alloc.y, self.corner,
                        self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX1, self.roundY1,
                        self.roundD, self.roundD, self.rightAngle,
                        self.rightAngle)
                gc.foreground = self.bordercolor
            if stopY > self.heightMINcorner:      # draw bottom left corner
                self.window.draw_rectangle(gc, True, self.alloc.x,
                        self.yPLUheightMINcorner, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX1, self.roundY2,
                        self.roundD, self.roundD, -self.rightAngle,
                        -self.rightAngle)
                gc.foreground = self.bordercolor
        if stopX > self.widthMINcorner:
            if startY < self.corner:              # draw top right corner
                self.window.draw_rectangle(gc, True, self.xPLUwidthMINcorner,
                        self.alloc.y, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX2, self.roundY1,
                        self.roundD, self.roundD, 0, self.rightAngle)
                gc.foreground = self.bordercolor
            if stopY > self.heightMINcorner:      # draw bottom right corner
                self.window.draw_rectangle(gc, True, self.xPLUwidthMINcorner,
                        self.yPLUheightMINcorner, self.corner, self.corner)
                gc.foreground = self.fillcolor
                self.window.draw_arc(gc, True, self.roundX2, self.roundY2,
                        self.roundD, self.roundD, 0, -self.rightAngle)
                gc.foreground = self.bordercolor

        gc.foreground = self.fillcolor
        if startX < self.widthMINcorner and stopX > self.corner:
            # draw centre fill
            if startY < self.heightMINborderW and stopY > self.borderW:
                self.window.draw_rectangle(gc, True, self.xPLUcorner,
                        self.yPLUborderW, self.widthMINcornerMUL2,
                        self.heightMINborderWMUL2)
        if startX < self.corner and stopX > self.borderW:
            # draw left fill
            if startY < self.heightMINcorner and stopY > self.corner:
                self.window.draw_rectangle(gc, True, self.xPLUborderW,
                        self.yPLUcorner, self.cornerMINborderW,
                        self.heightMINcornerMUL2)
        if startX < self.widthMINborderW and stopX > self.widthMINcorner:
            # draw right fill
            if startY < self.heightMINcorner and stopY > self.corner:
                self.window.draw_rectangle(gc, True, self.xPLUwidthMINcorner,
                        self.yPLUcorner, self.cornerMINborderW,
                        self.heightMINcornerMUL2)

        gc.foreground = saveForeground

        return False


class ImageButton(Gtk.Button):
    def __init__(self, mainImg_path, clickImg_path=None, enterImg_path=None,
            backgroundFill=None):

        Gtk.Button.__init__(self)
        self.alloc = None
        self.image = {}
        self.iwidth = {}
        self.iwidthDIV2 = {}
        self.iheight = {}
        self.iheightDIV2 = {}

        self.backgroundFill = backgroundFill

        def prepareImage(name, path):
            path = Config.imagefile(path)
            logging.error('ImageButton prepareImage %s', path)
            if path.endswith(".png"):
                pix = cairo.ImageSurface.create_from_png(path)
                self.is_png = True

            elif path.endswith(".svg"):
                pix = GdkPixbuf.Pixbuf.new_from_file(path)
                self.is_png = False

            self.image[name] = pix

            self.iwidth[name] = pix.get_width()
            self.iwidthDIV2[name] = self.iwidth[name] // 2
            self.iheight[name] = pix.get_height()
            self.iheightDIV2[name] = self.iheight[name] // 2

        prepareImage("main", mainImg_path)

        if enterImg_path != None:
            prepareImage("enter", enterImg_path)
            self.connect('enter-notify-event', self.on_btn_enter)
            self.connect('leave-notify-event', self.on_btn_leave)
        if clickImg_path != None:
            prepareImage("click", clickImg_path)
            self.connect('pressed', self.on_btn_press, None)
            self.connect('released', self.on_btn_release, None)
            if enterImg_path == None:
                self.image["enter"] = self.image["main"]
                self.iwidth["enter"] = self.iwidth["main"]
                self.iwidthDIV2["enter"] = self.iwidthDIV2["main"]
                self.iheight["enter"] = self.iheight["main"]
                self.iheightDIV2["enter"] = self.iheightDIV2["main"]
                self.connect('enter-notify-event', self.on_btn_enter)
                self.connect('leave-notify-event', self.on_btn_leave)

        self.curImage = self.upImage = "main"
        self.down = False

        self.connect('draw', self.draw)

    def draw(self, widget, cr):
        alloc = self.get_allocation()
        cr.rectangle(0, 0, alloc.width, alloc.height)
        if self.is_png:
            cr.set_source_surface(self.image[self.curImage], 0, 0)
            cr.paint()
        else:
            Gdk.cairo_set_source_pixbuf(cr, self.image[self.curImage], 0, 0)
            cr.paint()
        return True

    """
    def setImage(self, name, pix):
        print "setImage ", name, pix
        if name == "main" and self.image["main"] == self.image["enter"]:
            updateEnter = True
        else:
            updateEnter = False

        if pix.get_has_alpha():
            if self.backgroundFill == None:
                self.image[name] = pix
            else:
                self.image[name] = gtk.gdk.Pixmap( win,
                        pix.get_width(), pix.get_height() )
                colormap = self.get_colormap()
                self.gc.foreground = colormap.alloc_color(self.backgroundFill,
                        True, True )
                self.image[name].draw_rectangle( self.gc, True, 0, 0,
                        pix.get_width(), pix.get_height() )
                self.image[name].draw_pixbuf( self.gc, pix, 0, 0, 0, 0,
                        pix.get_width(), pix.get_height(),
                        gtk.gdk.RGB_DITHER_NONE )
        else:
            self.image[name] = gtk.gdk.Pixmap( win, pix.get_width(),
                    pix.get_height())
            self.image[name].draw_pixbuf( self.gc, pix, 0, 0, 0, 0,
                    pix.get_width(), pix.get_height(), gtk.gdk.RGB_DITHER_NONE)
        self.iwidth[name] = pix.get_width()
        self.iwidthDIV2[name] = self.iwidth[name]//2
        self.iheight[name] = pix.get_height()
        self.iheightDIV2[name] = self.iheight[name]//2

        if updateEnter:
            self.image["enter"] = self.image["main"]
            self.iwidth["enter"] = self.iwidth["main"]
            self.iwidthDIV2["enter"] = self.iwidthDIV2["main"]
            self.iheight["enter"] = self.iheight["main"]
            self.iheightDIV2["enter"] = self.iheightDIV2["main"]
            self.connect('enter-notify-event',self.on_btn_enter)
            self.connect('leave-notify-event',self.on_btn_leave)

        self.queue_draw()
    """

    def on_btn_press(self, widget, event):
        self.curImage = "click"
        self.down = True
        self.queue_draw()

    def on_btn_enter(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.upImage = "enter"
            if self.down:
                self.curImage = "click"
            else:
                self.curImage = "enter"
            self.queue_draw()

    def on_btn_leave(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.curImage = self.upImage = "main"
            self.queue_draw()

    def on_btn_release(self, widget, event):
        self.curImage = self.upImage
        self.down = False
        self.queue_draw()

    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.invoker = WidgetInvoker(self)
        self._palette.props.invoker._position_hint = WidgetInvoker.AT_CURSOR


class ImageToggleButton(Gtk.ToggleButton):

    def __init__(self, mainImg_path, altImg_path, enterImg_path=None,
            backgroundFill=None):
        mainImg_path = imagefile(mainImg_path)
        altImg_path = imagefile(altImg_path)
        enterImg_path = imagefile(enterImg_path)

        Gtk.ToggleButton.__init__(self)
        self.alloc = None
        self.within = False
        self.clicked = False
        self.is_png = True

        self.image = {}
        self.iwidth = {}
        self.iheight = {}

        self.backgroundFill = backgroundFill

        def prepareImage(name, path):
            if path.endswith(".png"):
                pix = cairo.ImageSurface.create_from_png(path)
                self.is_png = True

            elif path.endswith(".svg"):
                pix = GdkPixbuf.Pixbuf.new_from_file(path)
                self.is_png = False

            self.image[name] = pix

            self.iwidth[name] = pix.get_width()
            self.iheight[name] = pix.get_height()

        prepareImage("main", mainImg_path)
        prepareImage("alt", altImg_path)

        if enterImg_path != None:
            prepareImage("enter", enterImg_path)
        else:
            self.image["enter"] = self.image["main"]
            self.iwidth["enter"] = self.iwidth["main"]
            self.iheight["enter"] = self.iheight["main"]

        self.connect('enter-notify-event', self.on_btn_enter)
        self.connect('leave-notify-event', self.on_btn_leave)

        self.connect('toggled', self.toggleImage)
        self.connect('pressed', self.pressed)
        self.connect('released', self.released)
        self.connect('draw', self.draw)
        self.set_size_request(self.iwidth["main"], self.iheight["main"])

        self.toggleImage(self)

    def draw(self, widget, cr):
        alloc = self.get_allocation()

        cr.save()
        if self.is_png:
            img_surface = self.image[self.curImage]
            cr.translate((alloc.width - img_surface.get_width()) / 2,
                    (alloc.height - img_surface.get_height()) / 2)
            cr.set_source_surface(img_surface, 0, 0)
            cr.paint()
        else:
            pxb = self.image[self.curImage]
            cr.translate((alloc.width - pxb.get_width()) / 2,
                    (alloc.height - pxb.get_height()) / 2)
            Gdk.cairo_set_source_pixbuf(cr, pxb, 0, 0)
            cr.paint()
        cr.restore()
        return True

    def setImage(self, name, pix):
        if name == "main" and self.image["main"] == self.image["enter"]:
            updateEnter = True
        else:
            updateEnter = False

        if True:
            if self.backgroundFill == None:
                self.image[name] = pix
            else:
                self.image[name] = cairo.ImageSurface(cairo.FORMAT_RGB24,
                        pix.get_width(), pix.get_height())
                cxt = cairo.Context(self.image[name])
                #colormap = self.get_colormap()
                #self.gc.foreground = \
                #    colormap.alloc_color( self.backgroundFill, True, True )
                cxt.rectangle(0, 0, pix.get_width(), pix.get_height())
                cxt.fill()
                cxt.set_source_pixbuf(pix, 0, 0)
        else:
            self.image[name] = cairo.ImageSurface(cairo.FORMAT_RGB24,
                    pix.get_width(), pix.get_height())
            cxt = cairo.Context(self.image[name])
            cxt.set_source_pixbuf(pix, 0, 0)
        self.iwidth[name] = pix.get_width()
        self.iheight[name] = pix.get_height()

        if updateEnter:
            self.image["enter"] = self.image["main"]
            self.iwidth["enter"] = self.iwidth["main"]
            self.iheight["enter"] = self.iheight["main"]
            self.connect('enter-notify-event', self.on_btn_enter)
            self.connect('leave-notify-event', self.on_btn_leave)

        self.queue_draw()

    def toggleImage(self, widget):
        if not self.get_active():
            if self.within and "enter" in self.image:
                self.curImage = "enter"
            else:
                self.curImage = "main"
        else:
            self.curImage = "alt"
        self.queue_draw()

    def pressed(self, widget):
        self.clicked = True
        self.curImage = "alt"
        self.queue_draw()

    def released(self, widget):
        self.clicked = False
        self.toggleImage(self)

    def on_btn_enter(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.within = True
            if not self.get_active() and not self.clicked:
                self.curImage = "enter"
            else:
                self.curImage = "alt"
            self.queue_draw()

    def on_btn_leave(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.within = False
            if not self.get_active():
                self.curImage = "main"
            else:
                self.curImage = "alt"
            self.queue_draw()

    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.invoker = WidgetInvoker(self)
        self._palette.props.invoker._position_hint = WidgetInvoker.AT_CURSOR


class ImageRadioButton(Gtk.RadioButton):

    def __init__(self, group, mainImg_path, altImg_path, enterImg_path=None,
            backgroundFill=None):
        mainImg_path = imagefile(mainImg_path)
        altImg_path = imagefile(altImg_path)
        enterImg_path = imagefile(enterImg_path)

        Gtk.RadioButton.__init__(self)
        if group is not None:
            self.join_group(group)
        self.within = False
        self.clicked = False
        self.set_label('')
        self.image = {}
        self.iwidth = {}
        self.iwidthDIV2 = {}
        self.iheight = {}
        self.iheightDIV2 = {}

        self.backgroundFill = backgroundFill

        def prepareImage(name, path):
            if path.endswith(".png"):
                pix = cairo.ImageSurface.create_from_png(path)
                self.is_png = True

            elif path.endswith(".svg"):
                pix = GdkPixbuf.Pixbuf.new_from_file(path)
                self.is_png = False

            self.image[name] = pix

            self.iwidth[name] = pix.get_width()
            self.iwidthDIV2[name] = self.iwidth[name] // 2
            self.iheight[name] = pix.get_height()
            self.iheightDIV2[name] = self.iheight[name] // 2

        prepareImage("main", mainImg_path)
        prepareImage("alt", altImg_path)

        if enterImg_path != None:
            prepareImage("enter", enterImg_path)
        else:
            self.image["enter"] = self.image["main"]
            self.iwidth["enter"] = self.iwidth["main"]
            self.iwidthDIV2["enter"] = self.iwidthDIV2["main"]
            self.iheight["enter"] = self.iheight["main"]
            self.iheightDIV2["enter"] = self.iheightDIV2["main"]

        self.connect('enter-notify-event', self.on_btn_enter)
        self.connect('leave-notify-event', self.on_btn_leave)

        self.connect("toggled", self.toggleImage)
        self.connect('pressed', self.pressed)
        self.connect('released', self.released)
        self.connect('draw', self.draw)

        self.set_size_request(self.iwidth["main"], self.iheight["main"])

        self.curImage = "main"
        self.queue_draw()

    def draw(self, widget, cr):
        if self.is_png:
            cr.set_source_surface(self.image[self.curImage], 0, 0)
            cr.paint()
        else:
            Gdk.cairo_set_source_pixbuf(cr, self.image[self.curImage], 0, 0)
            cr.paint()
        return True

    def toggleImage(self, widget):
        if not self.get_active():
            if self.within and "enter" in self.image:
                self.curImage = "enter"
            else:
                self.curImage = "main"
        else:
            self.curImage = "alt"
        self.queue_draw()

    def pressed(self, widget):
        self.clicked = True
        self.curImage = "alt"
        self.queue_draw()

    def released(self, widget):
        self.curImage = "main"
        self.queue_draw()

    def on_btn_enter(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.within = True
            if not self.clicked:
                self.curImage = "enter"
            else:
                self.curImage = "alt"
            self.queue_draw()

    def on_btn_leave(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL:
            self.within = False
            if not self.clicked:
                self.curImage = "main"
            else:
                self.curImage = "alt"
            self.queue_draw()

    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.invoker = WidgetInvoker(self)
        self._palette.props.invoker._position_hint = WidgetInvoker.AT_CURSOR


class keyButton(Gtk.Button):

    def __init__(self, width, height, fillcolor, strokecolor):
        Gtk.Button.__init__(self)
        self.alloc = None
        
        # Store colors as Gdk.RGBA for GTK3 compatibility
        self.fillcolor = Gdk.RGBA()
        self.fillcolor.parse("rgb({},{},{})".format(
            int(fillcolor[0] * 255),
            int(fillcolor[1] * 255),
            int(fillcolor[2] * 255)
        ))
        
        self.strokecolor = Gdk.RGBA()
        self.strokecolor.parse("rgb({},{},{})".format(
            int(strokecolor[0] * 255),
            int(strokecolor[1] * 255),
            int(strokecolor[2] * 255)
        ))
        
        self.width = width
        self.height = height
        self.drawX = 0
        self.drawY = 0
        
        # Connect to the draw signal for GTK3
        self.connect('draw', self.on_draw)
        self.connect('size-allocate', self.on_size_allocate)
        
        self.set_size_request(self.width, self.height)

    def on_size_allocate(self, widget, allocation):
        self.alloc = allocation
        self.drawX = allocation.width // 2
        self.drawY = allocation.height // 2

    def on_draw(self, widget, cr):
        # Set up the drawing context
        Gtk.render_background(
            self.get_style_context(),
            cr,
            0, 0,
            self.alloc.width, self.alloc.height
        )
        
        # Draw the rounded rectangle
        cr.set_source_rgba(
            self.fillcolor.red,
            self.fillcolor.green,
            self.fillcolor.blue,
            self.fillcolor.alpha
        )
        
        # Calculate position to center the button
        x = self.drawX - self.width // 2
        y = self.drawY - self.height // 2
        
        # Draw the rounded rectangle using Cairo
        radius = 10
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.arc(x + self.width - radius, y + radius, radius, 3 * math.pi / 2, 0)
        cr.arc(x + self.width - radius, y + self.height - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + self.height - radius, radius, math.pi / 2, math.pi)
        cr.close_path()
        cr.fill()
        
        # Draw border
        cr.set_source_rgba(
            self.strokecolor.red,
            self.strokecolor.green,
            self.strokecolor.blue,
            self.strokecolor.alpha
        )
        cr.set_line_width(1)
        cr.stroke()
        
        return False  # Continue event propagation

    def set_fillcolor(self, r, g, b):
        self.fillcolor = Gdk.RGBA()
        self.fillcolor.parse("rgb({},{},{})".format(
            int(r * 255),
            int(g * 255),
            int(b * 255)
        ))
        self.queue_draw()

    def set_strokecolor(self, r, g, b):
        self.strokecolor = Gdk.RGBA()
        self.strokecolor.parse("rgb({},{},{})".format(
            int(r * 255),
            int(g * 255),
            int(b * 255)
        ))
        self.queue_draw()


class BigComboBox(Gtk.ComboBox):

    def __init__(self):
        Gtk.ComboBox.__init__(self)
        self.model = Gtk.ListStore(int, str)
        self.set_model(self.model)
        self.text_renderer = Gtk.CellRendererText()
        self.pack_start(self.text_renderer, True)
        self.add_attribute(self.text_renderer, "text", 1)

    def append_item(self, action_id, text, icon_name=None, size=None,
            pixbuf=None):

        if (icon_name or pixbuf):
            self._icon_renderer = Gtk.CellRendererPixbuf()

            settings = self.get_settings()
            _, w, h = Gtk.icon_size_lookup_for_settings(settings,
                    Gtk.IconSize.MENU)
            self._icon_renderer.props.stock_size = w

            self.pack_start(self._icon_renderer, False)
            self.add_attribute(self._icon_renderer, 'pixbuf', 2)

        #if text:
            #self._text_renderer = Gtk.CellRendererText()
            #self.pack_start(self._text_renderer, True)
            #self.add_attribute(self._text_renderer, 'text', 1)

        if not pixbuf:
            if icon_name:
                if not size:
                    size = Gtk.IconSize.LARGE_TOOLBAR
                    width, height = Gtk.icon_size_lookup(size)
                else:
                    width, height = size
                if icon_name[0:6] == "theme:":
                    icon_name = self._get_real_name_from_theme(icon_name[6:],
                            size)
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name,
                        width, height)
            else:
                pixbuf = None

        self.model.append([action_id, text])
