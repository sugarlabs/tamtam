from gi.repository import Gtk, Gdk, GObject
import cairo

from  common.Util.CSoundClient import new_csound_client
import common.Config as Config

KEY_MAP_PIANO = Config.KEY_MAP_PIANO

class Trackpad:
    def __init__(self, win):
        if not Config.FEATURES_GRAB_MOUSE:
            return

        self.win = win
        self.csnd = new_csound_client()
        win.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        win.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        win.connect('motion-notify-event',self.handle_motion)
        win.connect('key-press-event',self.handle_keyPress)
        win.connect('key-release-event',self.handle_keyRelease)

        self.first_x = None
        self.current_x = None
        self.final_x = None
        self.first_y = None
        self.current_y = None
        self.final_y = None
        
        self.buttonPressed = False
        
        #self.create_invisible_cursor()
        
        self.display = self.win.get_display()
        self.screen = Gdk.Display.get_default_screen(self.display)
        self.context = None
 
    def setContext(self, context):
        self.context = context

    #def create_invisible_cursor(self):
    #    pix_data = """/* XPM */
    #    static char * invisible_xpm[] = {
    #    "1 1 1 1",
    #    "       c None",
    #    " "};"""
    #    color = gtk.gdk.Color()
    #    pix = cairo.ImageSurface(cairo.FORMAT_RGB24, 0, 0)
    #    self.invisible_cursor = gtk.gdk.Cursor(pix,pix,color,color,0,0)
        
    def handle_motion(self,widget,event):
        if self.context != 'edit':
            if event.x < 0:
                X = 0
            elif event.x > self.screen.get_width():
                X = self.screen.get_width()
            else:
                X = event.x

            if event.y < 0:
                Y = 0
            elif event.y > self.screen.get_height():
                Y = self.screen.get_height()
            else:
                Y = event.y

            self.current_x = X
            self.current_y = Y
            if self.buttonPressed:
                self.final_x = X - self.first_x 
                self.final_y = Y - self.first_y
                self.csnd.setTrackpadX(self.final_x)
                self.csnd.setTrackpadY(self.final_y)
        
    def handle_keyPress(self,widget,event):
        if event.hardware_keycode in KEY_MAP_PIANO and self.buttonPressed == False:
            Gdk.Display.warp_pointer(self.display, self.screen, self.screen.get_width() / 2, self.screen.get_height() / 2)
            Gdk.pointer_grab(self.win.window, event_mask=Gdk.EventType.POINTER_MOTION_MASK)#, cursor = self.invisible_cursor)
            self.buttonPressed = True
            self.first_x = self.screen.get_width() / 2
            self.first_y = self.screen.get_height() / 2
    
    def handle_keyRelease(self,widget,event):
        if event.hardware_keycode in KEY_MAP_PIANO:            
            Gdk.pointer_ungrab(time = 0)
            self.buttonPressed = False
            self.restoreDelay = GObject.timeout_add(120, self.restore)

    def restore( self ):
        self.csnd.setTrackpadX(0)
        self.csnd.setTrackpadY(0)
        GObject.source_remove( self.restoreDelay )

