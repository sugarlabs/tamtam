from Framework.Constants import Constants
from Framework.Generation.GenerationConstants import GenerationConstants

    def __init__( self, onset, pitch, amplitude, pan, duration, trackID, tied = False, instrument = Constants.FLUTE ):
        self.pan = pan
        self.duration = duration
        self.trackID = trackID
        self.instrument = instrument
        self.tied = tied


        # duration for CSound is in seconds
        newPitch = self.getTranspositionFactor( self.pitch )

# condition only on instruments that allow tied notes
        if self.tied:
            newDuration = -1
        else:
            newDuration = self.duration*(1000/120)*0.001

#        if self.trackID == 0:
 #           self.instrument = Constants.SNARE
  #      elif self.trackID == 1:
#            self.instrument = Constants.WOOD
#        elif self.trackID == 2:
#            self.instrument = Constants.HHC
#        elif self.trackID == 3:
#            self.instrument = Constants.BD

                                                                            self.instrument, self.amplitude, self.pan)

        return pow( GenerationConstants.TWO_ROOT_TWELVE, pitch - 36 )
    def adjustDuration( self, amount ):