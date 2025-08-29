import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import shelve
from Generation.Generator import GenerationParameters
from Generation.GenerationConstants import GenerationConstants
from Util.ThemeWidgets import *
import Config

Tooltips = Config.Tooltips()

class GenerationParametersWindow(Gtk.Box):
    def __init__(self, generateFunction, handleCloseWindowCallback):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.handleCloseWindowCallback = handleCloseWindowCallback
        self.tooltips = Tooltips()

        self.rythmMethod = GenerationConstants.DEFAULT_RYTHM_METHOD
        self.pitchMethod = GenerationConstants.DEFAULT_PITCH_METHOD
        self.pattern = GenerationConstants.DEFAULT_PATTERN   
        self.scale = GenerationConstants.DEFAULT_SCALE
        self.sourceVariation = 1 
        self.generateFunction = generateFunction     
        self.setupWindow()
        self.show_all()
        
    def setupWindow( self ):
        self.GUI = {}
        self.rythmDensity = GenerationConstants.DEFAULT_DENSITY
        self.rythmRegularity = GenerationConstants.DEFAULT_RYTHM_REGULARITY
        self.pitchRegularity = GenerationConstants.DEFAULT_PITCH_REGULARITY 
        self.pitchStep = GenerationConstants.DEFAULT_STEP
        self.duration = GenerationConstants.DEFAULT_DURATION
        self.silence = GenerationConstants.DEFAULT_SILENCE

        # Generation Panel Setup
        generationBox = RoundVBox(fillcolor=Config.INST_BCK_COLOR, bordercolor=Config.PANEL_BCK_COLOR)
        generationBox.set_border_width(1)
        generationBox.set_radius(10)
        XYSlidersBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        rgba = Gdk.RGBA()
        rgba.parse(Config.PANEL_COLOR)
        self.col = rgba

        XYSlider1Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        XYSlider1UpBox = RoundHBox(fillcolor=Config.PANEL_COLOR, bordercolor=Config.INST_BCK_COLOR)
        XYSlider1UpBox.set_border_width(3)
        XYSlider1UpBox.set_radius(10)
        self.XYSlider1DownBox = RoundHBox(fillcolor=Config.PANEL_COLOR, bordercolor=Config.INST_BCK_COLOR)
        self.XYSlider1DownBox.set_border_width(3)
        self.XYSlider1DownBox.set_radius(10)

        self.slider1Label = Gtk.DrawingArea()
        self.slider1Label.override_background_color(Gtk.StateFlags.NORMAL, self.col)
        rgba = Gdk.RGBA()
        rgba.parse(Config.PANEL_COLOR)
        self.bgColor = rgba
        self.slider1Label.set_size_request(228, 60)
        self.slider1Label.connect("draw", self.draw )
        XYSliderBox1 = self.formatRoundBox( RoundFixed(), Config.PANEL_COLOR )
        XYSliderBox1.set_size_request( 250, 250 )
        self.GUI["XYButton1"] =  ImageToggleButton('XYbut.png',
                'XYbutDown.png', backgroundFill=Config.PANEL_COLOR)
        self.XAdjustment1 = Gtk.Adjustment(value=self.rythmDensity*100, lower=0, upper=100, step_increment=1, page_increment=1, page_size=0)
        self.XSlider1 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.XAdjustment1)
        self.XSlider1.set_draw_value(False)
        self.XSlider1.set_size_request(100, -1)
        self.XSlider1.connect("value-changed", self.XSlider1Changed)
        
        self.YAdjustment1 = Gtk.Adjustment(value=self.rythmRegularity*100, lower=0, upper=100, step_increment=1, page_increment=1, page_size=0)
        self.YSlider1 = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=self.YAdjustment1)
        self.YSlider1.set_inverted(True)
        self.YSlider1.set_draw_value(False)
        self.YSlider1.set_size_request(-1, 100)
        self.YSlider1.connect("value-changed", self.YSlider1Changed)
        XYSlider1UpBox.pack_start( self.XSlider1, False, False )
        XYSlider1UpBox.pack_start( self.YSlider1, False, False )

        self.XYSlider1DownBox.pack_start(self.slider1Label, False, False, 5)
        XYSlider1Box.pack_start(XYSlider1UpBox)
        XYSlider1Box.pack_start(self.XYSlider1DownBox)
        XYSlidersBox.pack_start(XYSlider1Box, False, False, 5)


        XYSlider2Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        XYSlider2UpBox = RoundHBox(fillcolor=Config.PANEL_COLOR, bordercolor=Config.INST_BCK_COLOR)
        XYSlider2UpBox.set_border_width(3)
        XYSlider2UpBox.set_radius(10)
        self.XYSlider2DownBox = RoundHBox(fillcolor=Config.PANEL_COLOR, bordercolor=Config.INST_BCK_COLOR)
        self.XYSlider2DownBox.set_border_width(3)
        self.XYSlider2DownBox.set_radius(10)

        self.slider2Label = Gtk.DrawingArea()
        self.slider2Label.override_background_color(Gtk.StateFlags.NORMAL, self.col)
        self.slider2Label.set_size_request(228, 60)
        self.slider2Label.connect("draw", self.draw2 )
        XYSliderBox2 = self.formatRoundBox( RoundFixed(), Config.PANEL_COLOR )
        XYSliderBox2.set_size_request( 250, 250 )
        self.GUI["XYButton2"] =  ImageToggleButton('XYbut.png',
                'XYbutDown.png', backgroundFill=Config.PANEL_COLOR)
        self.XAdjustment2 = Gtk.Adjustment(value=self.pitchRegularity*100, lower=0, upper=100, step_increment=1, page_increment=1, page_size=0)
        self.XSlider2 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.XAdjustment2)
        self.XSlider2.set_draw_value(False)
        self.XSlider2.set_size_request(100, -1)
        self.XSlider2.connect("value-changed", self.XSlider2Changed)
        
        self.YAdjustment2 = Gtk.Adjustment(value=self.pitchStep*100, lower=0, upper=100, step_increment=1, page_increment=1, page_size=0)
        self.YSlider2 = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=self.YAdjustment2)
        self.YSlider2.set_inverted(True)
        self.YSlider2.set_draw_value(False)
        self.YSlider2.set_size_request(-1, 100)
        self.YSlider2.connect("value-changed", self.YSlider2Changed)
        XYSlider2UpBox.pack_start( self.XSlider2, False, False )
        XYSlider2UpBox.pack_start( self.YSlider2, False, False )
        self.XAdjustment2.connect("value-changed", self.handleXAdjustment2)
        # Sliders are already created above with GTK3 compatible code
        self.YAdjustment2.connect("value-changed", self.YSlider2Changed)
        # Pack the sliders that were already created
        XYSlider2UpBox.pack_start(self.XSlider2, False, False)
        XYSlider2UpBox.pack_start(self.YSlider2, False, False)

        self.XYSlider2DownBox.pack_start(self.slider2Label, False, False, 5)
        XYSlider2Box.pack_start(XYSlider2UpBox)
        XYSlider2Box.pack_start(self.XYSlider2DownBox)
        XYSlidersBox.pack_start(XYSlider2Box, False, False, 5)


        XYSlider3Box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        XYSlider3UpBox = RoundHBox(fillcolor=Config.PANEL_COLOR, bordercolor=Config.INST_BCK_COLOR)
        XYSlider3UpBox.set_border_width(3)
        XYSlider3UpBox.set_radius(10)
        self.XYSlider3DownBox = RoundHBox(fillcolor=Config.PANEL_COLOR, bordercolor=Config.INST_BCK_COLOR)
        self.XYSlider3DownBox.set_border_width(3)
        self.XYSlider3DownBox.set_radius(10)

        self.slider3Label = Gtk.DrawingArea()
        self.slider3Label.override_background_color(Gtk.StateFlags.NORMAL, self.col)
        self.slider3Label.set_size_request(228, 60)
        self.slider3Label.connect("draw", self.draw3)
        
        # Create sliders for duration and silence
        self.XAdjustment3 = Gtk.Adjustment(value=self.duration*100, lower=0, upper=100, 
                                         step_increment=1, page_increment=1, page_size=0)
        self.XSlider3 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.XAdjustment3)
        self.XSlider3.set_draw_value(False)
        self.XSlider3.set_size_request(100, -1)
        self.XSlider3.connect("value-changed", self.XSlider3Changed)
        
        self.YAdjustment3 = Gtk.Adjustment(value=self.silence*100, lower=0, upper=100,
                                         step_increment=1, page_increment=1, page_size=0)
        self.YSlider3 = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=self.YAdjustment3)
        self.YSlider3.set_inverted(True)
        self.YSlider3.set_draw_value(False)
        self.YSlider3.set_size_request(-1, 100)
        self.YSlider3.connect("value-changed", self.YSlider3Changed)
        
        # Pack the sliders
        XYSlider3UpBox.pack_start(self.XSlider3, False, False, 0)
        XYSlider3UpBox.pack_start(self.YSlider3, False, False, 0)

        self.XYSlider3DownBox.pack_start(self.slider3Label, False, False, 5)
        XYSlider3Box.pack_start(XYSlider3UpBox)
        XYSlider3Box.pack_start(self.XYSlider3DownBox)
        XYSlidersBox.pack_start(XYSlider3Box, False, False, 5)

        generationBox.pack_start(XYSlidersBox, False, False, 5) 

        self.pack_start(generationBox)

        # Meta Algo panel setup
        metaAlgoBox = RoundVBox(fillcolor=Config.INST_BCK_COLOR, bordercolor=Config.PANEL_BCK_COLOR)
        metaAlgoBox.set_border_width(1)
        metaAlgoBox.set_radius(10)

        methodBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.firstButton = None
        methodNames = ['drunk', 'droneJump', 'repeat', 'loopSeg']
        for meth in methodNames:
            self.GUI[meth] = ImageRadioButton(self.firstButton, meth + '.png',
                    meth + 'Down.png', meth + 'Over.png',
                    backgroundFill=Config.INST_BCK_COLOR)
            if self.firstButton is None:
                self.firstButton = self.GUI[meth]
            self.GUI[meth].connect('clicked', self.handleMethod, methodNames.index(meth))
            if methodNames.index(meth) == self.pattern:
                self.GUI[meth].set_active(True)
            methodBox.pack_start(self.GUI[meth], False, False, 0)
        metaAlgoBox.pack_start(methodBox, False, False, 5)

        scaleBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.firstButton = None
        scaleNames = ['majorKey', 'minorHarmKey', 'minorKey', 'phrygienKey', 'dorienKey', 'lydienKey', 'myxoKey']
        for scale in scaleNames:
            self.GUI[scale] = ImageRadioButton(self.firstButton,
                    scale + '.png', scale + 'Down.png', scale + 'Over.png',
                    backgroundFill=Config.INST_BCK_COLOR)
            if self.firstButton is None:
                self.firstButton = self.GUI[scale]
            self.GUI[scale].connect('clicked' , self.handleScale , scaleNames.index(scale))
            if scaleNames.index(scale) == self.scale:
                self.GUI[scale].set_active(True)
            scaleBox.pack_start(self.GUI[scale], False, False)
        metaAlgoBox.pack_start(scaleBox, False, False)

        self.pack_start(metaAlgoBox)

        # Transport Panel Setup
        transportBox = RoundVBox(fillcolor=Config.INST_BCK_COLOR, bordercolor=Config.PANEL_BCK_COLOR)
        transportBox.set_border_width(1)
        transportBox.set_radius(10)

        # Create save/load presets
        transButtonBox = RoundHBox(fillcolor=Config.INST_BCK_COLOR, bordercolor=Config.PANEL_BCK_COLOR)
        transButtonBox.set_radius(10)

        self.GUI["saveButton"] = ImageButton('save.png',
                backgroundFill=Config.INST_BCK_COLOR)
        self.GUI["saveButton"].connect("clicked", self.handleSave, None)
        #transButtonBox.pack_start(self.GUI["saveButton"], False, False, 2)

        self.GUI["loadButton"] = ImageButton('load.png',
                backgroundFill=Config.INST_BCK_COLOR)
        self.GUI["loadButton"].connect("clicked", self.handleLoad, None)
        #transButtonBox.pack_start(self.GUI["loadButton"], False, False, 2)

        # create cancel/check button
        self.GUI["checkButton"] = ImageButton('check.png',
                backgroundFill=Config.INST_BCK_COLOR)
        self.GUI["checkButton"].connect("clicked", self.generate)

        self.GUI["cancelButton"] = ImageButton('closeA.png',
                backgroundFill=Config.INST_BCK_COLOR)
        self.GUI["cancelButton"].connect("clicked", self.cancel)

        # create play/stop buttons
        playButton = ImageToggleButton('playTogOff.png', 'playTogOn.png',
                backgroundFill=Config.INST_BCK_COLOR)
        selButton = ImageToggleButton('playAll.png', 'playSel.png',
                backgroundFill=Config.INST_BCK_COLOR)
        transButtonBox.pack_end(self.GUI["checkButton"], False, False, 10)
        transButtonBox.pack_end(self.GUI["cancelButton"], False, False)
        #transButtonBox.pack_end(selButton, False, False)
        #transButtonBox.pack_end(playButton, False, False)
        transportBox.pack_start(transButtonBox)

        self.pack_start(transportBox)
        self.loadPixmaps()          
        # set tooltips
        for key in self.GUI:
            if key in Tooltips.ALGO:
                self.tooltips.set_tip(self.GUI[key],Tooltips.ALGO[key])
 
    def loadPixmaps(self):
        # In GTK3, we'll use GdkPixbuf directly
        self.arrowPixmap = []
        for i in range(2):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file(
                    imagefile(['arrowSide.png', 'arrowUp.png'][i]))
                self.arrowPixmap.append(pix)
            except Exception as e:
                print(f"Error loading arrow image {i}: {e}")
                # Create a blank pixbuf as fallback
                self.arrowPixmap.append(GdkPixbuf.Pixbuf.new(
                    GdkPixbuf.Colorspace.RGB, True, 8, 24, 24))

        # Initialize pixmap lists
        self.rythDensPixmap = []
        self.rythRegPixmap = []
        self.pitchRegPixmap = []
        self.pitchStepPixmap = []
        self.durPixmap = []
        self.silencePixmap = []
        
        # Map pixmap lists to their corresponding image name prefixes
        pixmaps = [
            (self.rythDensPixmap, 'rythDens'),
            (self.rythRegPixmap, 'rythReg'),
            (self.pitchRegPixmap, 'pitReg'),
            (self.pitchStepPixmap, 'pitStep'),
            (self.durPixmap, 'durLen'),
            (self.silencePixmap, 'durDens')
        ]
        
        # Load all the pixmaps
        for pixmap_list, img_name in pixmaps:
            for i in range(6):
                try:
                    pix = GdkPixbuf.Pixbuf.new_from_file(
                        imagefile(f"{img_name}{i+1}.png"))
                    pixmap_list.append(pix)
                except Exception as e:
                    print(f"Error loading {img_name} image {i+1}: {e}")
                    # Create a blank pixbuf as fallback (90x60 is a common size for these images)
                    pixmap_list.append(GdkPixbuf.Pixbuf.new(
                        GdkPixbuf.Colorspace.RGB, True, 8, 90, 60))


    def draw(self, widget, cr):
        # Get the allocation (size) of the widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Set up the drawing context
        cr.set_source_rgba(1, 1, 1, 1)  # White background
        cr.paint()
        
        # Draw the first arrow (left arrow)
        if len(self.arrowPixmap) > 0:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[0], 0, 18)
            cr.paint()
        
        # Draw the first image (rythDens)
        imgX = min(5, max(0, 5 - int(self.rythmDensity * 5)))
        if len(self.rythDensPixmap) > imgX:
            Gdk.cairo_set_source_pixbuf(cr, self.rythDensPixmap[imgX], 24, 0)
            cr.paint()
        
        # Draw the second arrow (top arrow)
        if len(self.arrowPixmap) > 1:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[1], 114, 18)
            cr.paint()
        
        # Draw the second image (rythReg)
        imgY = min(5, max(0, 5 - int(self.rythmRegularity * 5)))
        if len(self.rythRegPixmap) > imgY:
            Gdk.cairo_set_source_pixbuf(cr, self.rythRegPixmap[imgY], 138, 0)
            cr.paint()
            
        return False

    def draw2(self, widget, cr):
        # Get the allocation (size) of the widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Set up the drawing context
        cr.set_source_rgba(1, 1, 1, 1)  # White background
        cr.paint()
        
        # Calculate image indices with bounds checking
        imgX = min(5, max(0, 5 - int(self.pitchRegularity * 5)))
        imgY = min(5, max(0, 5 - int(self.pitchStep * 5)))
        
        # Draw the first arrow (left arrow)
        if len(self.arrowPixmap) > 0:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[0], 0, 18)
            cr.paint()
        
        # Draw the first image (pitchReg)
        if len(self.pitchRegPixmap) > imgX:
            Gdk.cairo_set_source_pixbuf(cr, self.pitchRegPixmap[imgX], 24, 0)
            cr.paint()
        
        # Draw the second arrow (top arrow)
        if len(self.arrowPixmap) > 1:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[1], 114, 18)
            cr.paint()
        
        # Draw the second image (pitchStep)
        if len(self.pitchStepPixmap) > imgY:
            Gdk.cairo_set_source_pixbuf(cr, self.pitchStepPixmap[imgY], 138, 0)
            cr.paint()
            
        return False

    def draw3(self, widget, cr):
        # Get the allocation (size) of the widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Set up the drawing context
        cr.set_source_rgba(1, 1, 1, 1)  # White background
        cr.paint()
        
        # Calculate image indices with bounds checking
        imgX = min(5, max(0, 5 - int(self.duration * 5)))
        imgY = min(5, max(0, 5 - int(self.silence * 5)))
        
        # Draw the first arrow (left arrow)
        if len(self.arrowPixmap) > 0:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[0], 0, 18)
            cr.paint()
        
        # Draw the first image (duration)
        if len(self.durPixmap) > imgX:
            Gdk.cairo_set_source_pixbuf(cr, self.durPixmap[imgX], 24, 0)
            cr.paint()
        
        # Draw the second arrow (top arrow)
        if len(self.arrowPixmap) > 1:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[1], 114, 18)
            cr.paint()
        
        # Draw the second image (silence)
        if len(self.silencePixmap) > imgY:
            Gdk.cairo_set_source_pixbuf(cr, self.silencePixmap[imgY], 138, 0)

    def draw2(self, widget, cr):
        # Get the allocation (size) of the widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Set up the drawing context
        cr.set_source_rgba(1, 1, 1, 1)  # White background
        cr.paint()
        
        # Calculate image indices with bounds checking
        imgX = min(5, max(0, 5 - int(self.pitchRegularity * 5)))
        imgY = min(5, max(0, 5 - int(self.pitchStep * 5)))
        
        # Draw the first arrow (left arrow)
        if len(self.arrowPixmap) > 0:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[0], 0, 18)
            cr.paint()
        
        # Draw the first image (pitchReg)
        if len(self.pitchRegPixmap) > imgX:
            Gdk.cairo_set_source_pixbuf(cr, self.pitchRegPixmap[imgX], 24, 0)
            cr.paint()
        
        # Draw the second arrow (top arrow)
        if len(self.arrowPixmap) > 1:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[1], 114, 18)
            cr.paint()
        
        # Draw the second image (pitchStep)
        if len(self.pitchStepPixmap) > imgY:
            Gdk.cairo_set_source_pixbuf(cr, self.pitchStepPixmap[imgY], 138, 0)
            cr.paint()
            
        return False

    def draw3(self, widget, cr):
        # Get the allocation (size) of the widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Set up the drawing context
        cr.set_source_rgba(1, 1, 1, 1)  # White background
        cr.paint()
        
        # Calculate image indices with bounds checking
        imgX = min(5, max(0, 5 - int(self.duration * 5)))
        imgY = min(5, max(0, 5 - int(self.silence * 5)))
        
        # Draw the first arrow (left arrow)
        if len(self.arrowPixmap) > 0:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[0], 0, 18)
            cr.paint()
        
        # Draw the first image (duration)
        if len(self.durPixmap) > imgX:
            Gdk.cairo_set_source_pixbuf(cr, self.durPixmap[imgX], 24, 0)
            cr.paint()
        
        # Draw the second arrow (top arrow)
        if len(self.arrowPixmap) > 1:
            Gdk.cairo_set_source_pixbuf(cr, self.arrowPixmap[1], 114, 18)
            cr.paint()
        
        # Draw the second image (silence)
        if len(self.silencePixmap) > imgY:
            Gdk.cairo_set_source_pixbuf(cr, self.silencePixmap[imgY], 138, 0)
            cr.paint()
            
        return False

    def XSlider1Changed(self, adjustment):
        self.rythmDensity = adjustment.get_value() / 100.0
        self.slider1Label.queue_draw()

    def YSlider1Changed(self, adjustment):
        self.rythmRegularity = adjustment.get_value() / 100.0
        self.slider1Label.queue_draw()

    def XSlider2Changed(self, adjustment):
        self.pitchRegularity = adjustment.get_value() / 100.0
        self.slider2Label.queue_draw()

    def YSlider2Changed(self, adjustment):
        self.pitchStep = adjustment.get_value() / 100.0
        self.slider2Label.queue_draw()

    def XSlider3Changed(self, adjustment):
        self.duration = adjustment.get_value() / 100.0
        self.slider3Label.queue_draw()

    def YSlider3Changed(self, adjustment):
        self.silence = adjustment.get_value() / 100.0
        self.slider3Label.queue_draw()
        
    def getGenerationParameters(self):
        return GenerationParameters(
            self.rythmDensity,
            self.rythmRegularity,
            self.pitchStep,
            self.pitchRegularity,
            self.duration,
            self.silence,
            self.rythmMethod,
            self.pitchMethod,
            self.pattern,
            self.scale
        )

    def cancel( self, widget, data=None ):
        self.handleCloseWindowCallback()

    def generate(self, widget, data=None):
        self.generateFunction( self.getGenerationParameters() )
        self.handleCloseWindowCallback()

    def handleMethod( self, widget, method ):
        if widget.get_active():
            self.pattern = method

    def handleScale( self, widget, scale ):
        if widget.get_active():
            self.scale = scale

    def formatRoundBox( self, box, fillcolor ):
        box.set_radius( 10 )
        box.set_border_width( 1 )
        box.set_fill_color( fillcolor )
        box.set_border_color( Config.INST_BCK_COLOR )
        return box


#=========================== PRESETS ================================

    def handleSave(self, widget, data=None):
        chooser = Gtk.FileChooserNative.new(
            title="Save Preset",
            transient_for=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE,
            accept_label="_Save",
            cancel_label="_Cancel"
        )
        
        response = chooser.run()
        if response == Gtk.ResponseType.ACCEPT:
            try: 
                filename = chooser.get_filename()
                print('INFO: save preset file %s' % filename)
                f = shelve.open(filename, 'n')
                self.saveState(f)
                f.close()
            except IOError as e: 
                print('ERROR: failed to save preset to file %s: %s' % (filename, str(e)))
        
        chooser.destroy()
    
    def handleLoad(self, widget, data=None):
        chooser = Gtk.FileChooserNative.new(
            title="Load Preset",
            transient_for=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Open",
            cancel_label="_Cancel"
        )
        
        response = chooser.run()
        if response == Gtk.ResponseType.ACCEPT:
            try: 
                filename = chooser.get_filename()
                print('INFO: load preset state from file %s' % filename)
                f = shelve.open(filename, 'r')
                self.loadState(f)
                f.close()
            except IOError as e: 
                print('ERROR: failed to load preset state from file %s: %s' % (filename, str(e)))
        
        chooser.destroy()

    def loadState( self, state ):
        pass
        self.rythmDensity = state['rythmDensity']
        self.rythmRegularity = state['rythmRegularity']
        self.pitchRegularity = state['pitchRegularity']
        self.pitchStep = state['pitchStep']
        self.duration = state['duration']
        self.silence = state['silence']
        self.pattern = state['pattern']
        self.scale = state['scale']

        self.XAdjustment1.set_value(self.rythmDensity*100)
        self.YAdjustment1.set_value(self.rythmRegularity*100)
        self.XAdjustment2.set_value(self.pitchRegularity*100)
        self.YAdjustment2.set_value(self.pitchStep*100)
        self.XAdjustment3.set_value(self.duration*100)
        self.YAdjustment3.set_value(self.silence*100)

    def saveState( self, state ):
        pass
        state['rythmDensity'] = self.rythmDensity
        state['rythmRegularity'] = self.rythmRegularity
        state['pitchRegularity'] = self.pitchRegularity
        state['pitchStep'] = self.pitchStep
        state['duration'] = self.duration
        state['silence'] = self.silence
        state['pattern'] = self.pattern
        state['scale'] = self.scale
