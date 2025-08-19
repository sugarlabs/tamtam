from gi.repository import Gtk


#----------------------------------------------------------------------
# A verical bar used to show the current point in time on a page
# TODO: modify this class to change the current point in time
#       on click and drag
#----------------------------------------------------------------------
class PositionIndicator( Gtk.DrawingArea ):
    #-----------------------------------
    # initialization
    #-----------------------------------
    def __init__( self, trackIDs, selectedTrackIDs, mutedTrackIDs ):
        Gtk.DrawingArea.__init__( self )
        
        self.trackIDs = trackIDs
        self.selectedTrackIDs = selectedTrackIDs
        self.mutedTrackIDs = mutedTrackIDs

        self.connect( "draw", self.draw )

    def draw( self, widget, cr ):
        indicatorSize = self.get_allocation()
        trackHeight = indicatorSize.height / len( self.trackIDs )
        
        trackIndex = 0
        for trackID in self.trackIDs:
            height = trackIndex * trackHeight
 
            cr.move_to( 0, height )
            cr.rel_line_to( indicatorSize.width, 0 )
            cr.rel_line_to( 0, height + trackHeight )
            cr.rel_line_to( -indicatorSize.width, 0 )
            cr.close_path()

            if trackID not in self.mutedTrackIDs:
                cr.set_source_rgb( 0, 0, 0 ) #black
            else:
                cr.set_source_rgb( 0.6, 0.6, 0.6 ) #grey
 
            cr.fill_preserve()
            cr.stroke()
            
            trackIndex += 1
