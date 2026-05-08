import array
import os
import select
import socket
import struct
import time

# CSound-compatible implementations of SuperCollider functions
def sc_inputMessage(msg):
    """Handle input messages in a CSound-compatible way"""
    if not hasattr(sc_inputMessage, 'cs'):
        sc_inputMessage.cs = None
    
    if sc_inputMessage.cs is None and hasattr(_Client, 'cs'):
        sc_inputMessage.cs = _Client.cs
    
    if sc_inputMessage.cs:
        # Convert SuperCollider message to CSound score event if needed
        if msg.startswith('/note'):
            # Example: /note [node, freq, amp, dur, pan]
            parts = msg.split()
            if len(parts) >= 5:
                freq = float(parts[1])
                amp = float(parts[2])
                dur = float(parts[3])
                pan = float(parts[4])
                # Create a CSound score event
                score = f'i 1 0 {dur} {freq} {amp} {pan}'
                sc_inputMessage.cs.readScore(score)
    
    if Config.DEBUG > 2:
        print(f'DEBUG: sc_inputMessage: {msg}')

def sc_loop_delete(loopId, noteId):
    """Delete a note from a loop using CSound"""
    if not hasattr(_Client, 'cs') or not _Client.cs:
        if Config.DEBUG > 0:
            print('ERROR: CSound not initialized in sc_loop_delete')
        return
    
    # In CSound, we can send a negative p3 to turn off a note
    score = f'i -1 0 0 {noteId}'
    _Client.cs.readScore(score)
    
    if Config.DEBUG > 2:
        print(f'DEBUG: sc_loop_delete - loopId: {loopId}, noteId: {noteId}')

def sc_loop_updateEvent(loopId, noteId, parameter, value, cmd=-1):
    """Update a note parameter in a loop using CSound"""
    if not hasattr(_Client, 'cs') or not _Client.cs:
        if Config.DEBUG > 0:
            print('ERROR: CSound not initialized in sc_loop_updateEvent')
        return
    
    # Get current time in seconds
    current_time = time.time()
    
    # Create a score event to update the parameter
    # Format: i p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 p11 p12 p13 p14 p15
    # Where p1 is negative to indicate a parameter update
    score = f'i -1 {current_time} 0 {noteId} {parameter} {value}'
    _Client.cs.readScore(score)
    
    if Config.DEBUG > 2:
        print(f'DEBUG: sc_loop_updateEvent - loopId: {loopId}, noteId: {noteId}, param: {parameter}, value: {value}')

def sc_destroy():
    """Clean up CSound resources"""
    if hasattr(_Client, 'cs') and _Client.cs:
        _Client.cs.cleanup()
        _Client.cs.reset()
        if Config.DEBUG > 1:
            print('DEBUG: CSound resources cleaned up')

def sc_initialize(csd_file=None):
    """Initialize CSound with optional CSD file"""
    if not hasattr(_Client, 'cs'):
        _Client.cs = csound.Csound()
        _Client.cs.setOption("-+rtaudio=alsa")
        _Client.cs.setOption("-odac")
        _Client.cs.setOption("-m0")
        _Client.cs.setOption("-d")
        
        if csd_file and os.path.exists(csd_file):
            result = _Client.cs.compile_(csd_file)
            if result == 0:
                _Client.cs.start()
                _Client.performance_thread = threading.Thread(target=_Client.cs.perform)
                _Client.performance_thread.start()
                return 0
            return -1
        return 0
    return 0

def sc_start(periods_per_buffer=2):
    """Start CSound performance"""
    if hasattr(_Client, 'cs') and _Client.cs:
        _Client.periods_per_buffer = periods_per_buffer
        _Client.cs.setOption(f"-b{periods_per_buffer * _Client.cs.getKsmps()}")
        _Client.cs.start()
        _Client.performance_thread = threading.Thread(target=_Client.cs.perform)
        _Client.performance_thread.start()
        return 0
    return -1

def sc_stop():
    """Stop CSound performance"""
    if hasattr(_Client, 'cs') and _Client.cs:
        _Client.cs.stop()
        if hasattr(_Client, 'performance_thread'):
            _Client.performance_thread.join()
        _Client.cs.cleanup()
        _Client.cs.reset()
        return 0
    return -1

def sc_scoreEvent(ev_type, params):
    """Send a score event to CSound"""
    if not hasattr(_Client, 'cs') or not _Client.cs:
        return -1
    
    # Convert event type to CSound p1
    p1 = 1  # Default instrument number
    if isinstance(ev_type, str):
        if ev_type.lower() == 'i':
            p1 = 1
        # Add more event type mappings as needed
    
    # Create score event string
    score = f"{ev_type} {p1} " + " ".join(str(p) for p in params)
    _Client.cs.readScore(score)
    return 0

def sc_setChannel(name, value):
    """Set a CSound control channel"""
    if hasattr(_Client, 'cs') and _Client.cs:
        _Client.cs.setControlChannel(name, value)
        return 0
    return -1

def sc_getTickf():
    """Get current tick position as float"""
    if hasattr(_Client, 'cs') and _Client.cs:
        return _Client.cs.getScoreTime() / _Client.tick_duration
    return 0.0
import sys
import threading
import time

from math import sqrt

import ctcsound as csound
import common.Config as Config

from common.Generation.GenerationConstants import GenerationConstants
from common.Util import NoteDB
import common.Util.InstrumentDB as InstrumentDB

loadedInstruments = []

_note_template = array.array('f' if struct.calcsize("P") == 4 else 'd', [0] * 19)


def _new_note_array():
    return _note_template.__copy__()

def _noteid(dbnote):
    return (dbnote.page << 16) + dbnote.id

_loop_default=0


class _CSoundClientPlugin:

    #array index constants for csound
    (INSTR_TRACK, \
    ONSET, \
    DURATION, \
    PITCH,
    REVERBSEND, \
    AMPLITUDE, \
    PAN, \
    INST_ID, \
    ATTACK, \
    DECAY, \
    FILTERTYPE, \
    FILTERCUTOFF, \
    INSTRUMENT2 ) = list(range(13))

    def __init__(self):
        self.cs = csound.Csound()
        self.cs.setOption("-+rtaudio=alsa")
        self.cs.setOption("-odac")
        self.cs.setOption("-m0")
        self.cs.setOption("-d")
        self.cs.compile_(Config.PLUGIN_UNIVORC)
        self.on = False
        self.periods_per_buffer = 2
        global _loop_default
        _loop_default = self.loopCreate()
        self.instrumentDB = InstrumentDB.getRef()
        self.jamesSux = {}

    def __del__(self):
        self.connect(False)
        if hasattr(self, 'cs'):
            self.cs.cleanup()
            self.cs.reset()

    def setChannel(self, name, val):
        self.cs.setControlChannel(name, val)

    def setMasterVolume(self, volume):
        self.cs.setControlChannel('masterVolume', volume)

    def setTrackVolume(self, volume, trackId):
        self.cs.setControlChannel('trackVolume' + str(trackId + 1), volume)

    def setTrackpadX(self, value):
        self.cs.setControlChannel('trackpadX', value)

    def setTrackpadY(self, value):
        self.cs.setControlChannel('trackpadY', value)

    def micRecording(self, table):
        # TODO: Implement mic recording functionality
        pass

    def load_mic_instrument(self, inst):
        fileName = Config.DATA_DIR + '/' + inst
        instrumentId = Config.INSTRUMENT_TABLE_OFFSET + self.instrumentDB.instNamed[inst].instrumentId
        # TODO: Implement instrument loading
        pass

    def load_synth_instrument(self, inst):
        fileName = Config.DATA_DIR + '/' + inst
        instrumentId = Config.INSTRUMENT_TABLE_OFFSET + self.instrumentDB.instNamed[inst].instrumentId
        sc_inputMessage(Config.CSOUND_LOAD_INSTRUMENT % (instrumentId, fileName))

    def load_ls_instrument(self, inst):
        fileName = Config.DATA_DIR + '/' + inst
        sc_inputMessage(Config.CSOUND_LOAD_LS_INSTRUMENT % fileName)

    def load_instruments(self):
        for instrumentSoundFile in list(self.instrumentDB.instNamed.keys()):
            if instrumentSoundFile[0:3] == 'mic' or instrumentSoundFile[0:3] == 'lab' or self.instrumentDB.instNamed[instrumentSoundFile].category == 'mysounds':
                fileName = Config.DATA_DIR + '/' + instrumentSoundFile
            else:
                fileName = Config.SOUNDS_DIR + "/" + instrumentSoundFile
            instrumentId = Config.INSTRUMENT_TABLE_OFFSET + self.instrumentDB.instNamed[ instrumentSoundFile ].instrumentId
            sc_inputMessage( Config.CSOUND_LOAD_INSTRUMENT % (instrumentId, fileName) )

    def load_instrument(self, inst):
        if not inst in loadedInstruments:
            if inst[0:3] == 'mic' or inst[0:3] == 'lab' or self.instrumentDB.instNamed[inst].category == 'mysounds':
                if os.path.isfile(os.path.join(Config.DATA_DIR, inst)):
                    fileName = os.path.join(Config.DATA_DIR, inst)
                else:
                    fileName = os.path.join(Config.SOUNDS_DIR, 'armbone')
            else:
                fileName = os.path.join(Config.SOUNDS_DIR, inst)
            
            instrumentId = Config.INSTRUMENT_TABLE_OFFSET + self.instrumentDB.instNamed[inst].instrumentId
            
            # Use CSound's score event to load the instrument
            # Format: i <instrument_number> <start_time> <duration> <p4> <p5> ...
            # For loading, we'll use a special instrument number (1000) and pass the filename as a string p-field
            load_cmd = 'i %d 0 -1 "%s"' % (1000, fileName)
            self.cs.readScore(load_cmd)
            
            # Store the instrument ID for later reference
            if not hasattr(self, 'loaded_instruments'):
                self.loaded_instruments = {}
            self.loaded_instruments[instrumentId] = fileName
            
            loadedInstruments.append(inst)

    def load_drumkit(self, kit):
        if not kit in loadedInstruments:
            for i in list(self.instrumentDB.instNamed[kit].kit.values()):
                fileName = Config.SOUNDS_DIR + "/" + i
                instrumentId = Config.INSTRUMENT_TABLE_OFFSET + self.instrumentDB.instNamed[i].instrumentId
                # TODO: Implement drumkit loading
                loadedInstruments.append(i)
            loadedInstruments.append(kit)

    def connect(self, init=True):
        if not init and self.on:
            if hasattr(self, 'cs'):
                self.cs.stop()
            self.on = False
        elif init and not self.on:
            if hasattr(self, 'cs'):
                self.cs.start()
                self.cs.performKsmps()
            self.on = True

    def destroy(self):
        self.connect(False)
        if hasattr(self, 'cs'):
            self.cs.cleanup()
            self.cs.reset()

    def inputMessage(self, msg):
        # TODO: Implement message passing to CSound
        pass

    def getTick(self):
        # TODO: Implement proper tick tracking
        return 0

    def adjustTick(self, amt):
        # TODO: Implement tick adjustment
        pass

    def setTempo(self, t):
        if (Config.DEBUG > 3): 
            print('INFO: loop tempo: %f -> %f' % (t, 60.0 / (Config.TICKS_PER_BEAT * t)))
        self.tick_duration = 60.0 / (Config.TICKS_PER_BEAT * t)
        # Set the tempo in CSound using a control channel
        self.cs.setControlChannel('tempo', t)


    def loopCreate(self):
        # TODO: Implement proper loop creation
        return 1

    def loopDestroy(self, loopId):
        sc_loop_delete(loopId)
        try:
            del self.jamesSux[ loopId ]
        except:
            pass

    def loopClear(self):
        global _loop_default
        # Clear all score events for the default loop
        if hasattr(self, 'cs') and self.cs:
            # Send a score event to clear all notes
            self.cs.readScore('i 999 0 -1 0')  # Special instrument to handle clearing
        
        # Reset the default loop
        _loop_default = 1  # Simple integer ID for the loop
        
        # Clear any loop-specific data
        if hasattr(self, 'jamesSux') and _loop_default in self.jamesSux:
            del self.jamesSux[_loop_default]


    def loopDelete(self, dbnote, loopId=_loop_default):
        """Delete a note from a loop by its database note ID.
        
        Args:
            dbnote: The database note to delete
            loopId: The ID of the loop to delete from (defaults to _loop_default)
        """
        if hasattr(self, 'cs') and self.cs:
            # Convert the note ID to a string and send a score event to delete it
            note_id = str(_noteid(dbnote))
            self.cs.readScore(f'i -1 0 0 {note_id}')  # Negative instrument number for deletion

    def loopDelete1(self, page, id, loopId=_loop_default):
        """Delete a note from a loop by page and ID.
        
        Args:
            page: The page number of the note
            id: The ID of the note within the page
            loopId: The ID of the loop to delete from (defaults to _loop_default)
        """
        if hasattr(self, 'cs') and self.cs:
            # Combine page and ID into a single identifier
            note_id = (page << 16) + id
            self.cs.readScore(f'i -1 0 0 {note_id}')  # Negative instrument number for deletion

    def loopStart(self, loopId=_loop_default):
        # TODO: Implement loop start
        pass

    def loopPause(self, loopId=_loop_default):
        # TODO: Implement loop pause
        pass

    def loopSetTick(self, t, loopId=_loop_default):
        # TODO: Implement loop tick setting
        pass

    def loopGetTick(self, loopId=_loop_default):
        # TODO: Implement loop tick getting
        return 0

    def loopSetNumTicks(self, n, loopId=_loop_default):
        """Set the number of ticks for a loop.
        
        Args:
            n: Number of ticks
            loopId: ID of the loop to modify (defaults to _loop_default)
        """
        if not hasattr(self, 'jamesSux'):
            self.jamesSux = {}
        self.jamesSux[loopId] = n
        # Update CSound with the new loop length if needed
        if hasattr(self, 'cs') and self.cs:
            # Convert ticks to seconds using the current tempo
            duration_seconds = n * self.tick_duration if hasattr(self, 'tick_duration') else n * 0.1  # Fallback to 0.1s per tick
            self.cs.setControlChannel(f'loop_{loopId}_length', duration_seconds)

    def loopGetNumTicks( self, loopId = _loop_default ):
        return self.jamesSux[loopId]

    def loopSetTickDuration(self, d, loopId=_loop_default):
        """Set the duration of each tick in seconds for a loop.
        
        Args:
            d: Duration of each tick in seconds
            loopId: ID of the loop to modify (defaults to _loop_default)
        """
        if not hasattr(self, 'tick_durations'):
            self.tick_durations = {}
        self.tick_durations[loopId] = d
        # Update the global tick duration if this is the active loop
        if loopId == _loop_default:
            self.tick_duration = d
        # Update CSound with the new tick duration
        if hasattr(self, 'cs') and self.cs:
            self.cs.setControlChannel(f'loop_{loopId}_tick_duration', d)

    def loopDeactivate(self, note='all', loopId=_loop_default):
        """Deactivate notes in a loop.
        
        Args:
            note: 'all' to deactivate all notes, or a specific note to deactivate
            loopId: ID of the loop to modify (defaults to _loop_default)
        """
        if note == 'all':
            # Deactivate all notes in the loop
            if hasattr(self, 'cs') and self.cs:
                # Send a special score event to deactivate all notes
                self.cs.readScore(f'i -2 0 0 {loopId} 0 0 0 0 0 0 0 0 0 0 0 0')
        else:
            # Deactivate a specific note
            if Config.DEBUG > 0:
                print('ERROR: deactivating a single note is not implemented')

    def loopUpdate(self, note, parameter, value,cmd, loopId=_loop_default):
        page = note.page
        track = note.track
        id = note.id
        if note.cs.mode == 'mini':
            instrument_id_offset = 0
        elif note.cs.mode == 'edit':
            if self.instrumentDB.instId[note.cs.instrumentId].kit != None:
                instrument_id_offset = 0
            else:
                instrument_id_offset = 100
        if (parameter == NoteDB.PARAMETER.ONSET):
            if (Config.DEBUG > 2): print('INFO: updating onset', (page<<16)+id, value)
            sc_loop_updateEvent( loopId, (page<<16)+id, 1, value, cmd)
        elif (parameter == NoteDB.PARAMETER.PITCH):
            if (Config.DEBUG > 2): print('INFO: updating pitch', (page<<16)+id, value)
            pitch = value
            if self.instrumentDB.instId[note.cs.instrumentId].kit != None:
                instrument = self.instrumentDB.instNamed[
                        self.instrumentDB.instId[note.cs.instrumentId].kit[pitch]]
                csoundInstId = instrument.csoundInstrumentId
                csoundTable  = Config.INSTRUMENT_TABLE_OFFSET + instrument.instrumentId
                if (Config.DEBUG > 2): print('INFO: updating drum instrument (pitch)', (page<<16)+id, instrument.name, csoundInstId)
                sc_loop_updateEvent( loopId, (page<<16)+id, 0, (csoundInstId + instrument_id_offset) + note.track * 0.01, -1 )
                sc_loop_updateEvent( loopId, (page<<16)+id, 7, csoundTable  , -1 )
                pitch = 1
            else:
                pitch = GenerationConstants.TRANSPOSE[ pitch - 24 ]
            sc_loop_updateEvent( loopId, (page<<16)+id, 3, pitch, cmd)
        elif (parameter == NoteDB.PARAMETER.AMPLITUDE):
            if (Config.DEBUG > 2): print('INFO: updating amp', (page<<16)+id, value)
            sc_loop_updateEvent( loopId, (page<<16)+id, 5, value, cmd)
        elif (parameter == NoteDB.PARAMETER.DURATION):
            if (Config.DEBUG > 2): print('INFO: updating duration', (page<<16)+id, value)
            sc_loop_updateEvent( loopId, (page<<16)+id, self.DURATION, value, cmd)
        elif (parameter == NoteDB.PARAMETER.INSTRUMENT):
            pitch = note.cs.pitch
            instrument = self.instrumentDB.instId[value]
            if instrument.kit != None:
                instrument = self.instrumentDB.instNamed[instrument.kit[pitch]]
            csoundInstId = instrument.csoundInstrumentId
            csoundTable  = Config.INSTRUMENT_TABLE_OFFSET + instrument.instrumentId
            loopStart = instrument.loopStart
            loopEnd = instrument.loopEnd
            crossDur = instrument.crossDur
            if (Config.DEBUG > 2): print('INFO: updating instrument', (page<<16)+id, instrument.name, csoundInstId)
            sc_loop_updateEvent( loopId, (page<<16)+id, 0, (csoundInstId + (track+1) + instrument_id_offset) + note.track * 0.01, cmd )
            sc_loop_updateEvent( loopId, (page<<16)+id, 7, csoundTable, -1 )
            sc_loop_updateEvent( loopId, (page<<16)+id, 12, loopStart, -1 )
            sc_loop_updateEvent( loopId, (page<<16)+id, 13, loopEnd, -1 )
            sc_loop_updateEvent( loopId, (page<<16)+id, 14, crossDur , -1 )
        elif (parameter == NoteDB.PARAMETER.PAN):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.PAN, value, cmd)
        elif (parameter == NoteDB.PARAMETER.REVERB):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.REVERBSEND, value, cmd)
        elif (parameter == NoteDB.PARAMETER.ATTACK):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.ATTACK, value, cmd)
        elif (parameter == NoteDB.PARAMETER.DECAY):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.DECAY, value, cmd)
        elif (parameter == NoteDB.PARAMETER.FILTERTYPE):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.FILTERTYPE, value, cmd)
        elif (parameter == NoteDB.PARAMETER.FILTERCUTOFF):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.FILTERCUTOFF, value, cmd)
        elif (parameter == NoteDB.PARAMETER.INSTRUMENT2):
            sc_loop_updateEvent( loopId, (page<<16)+id, self.INSTRUMENT2, value, cmd)
        else:
            if (Config.DEBUG > 0): print('ERROR: loopUpdate(): unsupported parameter change')

    def loopPlay(self, dbnote, active, storage=_new_note_array(), loopId=_loop_default):
        """Play or stop a note in a loop using CSound.
        
        Args:
            dbnote: The database note to play/stop
            active: 1 to start the note, 0 to stop it
            storage: Array to store note data (unused in this implementation)
            loopId: ID of the loop to modify (defaults to _loop_default)
        """
        if not hasattr(self, 'cs') or not self.cs:
            if Config.DEBUG > 0:
                print('ERROR: CSound not initialized')
            return

        # Convert the note to CSound parameters
        params = self.csnote_to_array(dbnote.cs, storage)
        
        # For CSound, we'll use a score event to play the note
        # Format: i p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 p11 p12 p13 p14 p15
        # Where:
        # p1: instrument number
        # p2: start time (beats)
        # p3: duration (beats)
        # p4-p15: instrument parameters
        
        # Get current tick position in the loop
        current_tick = self.loopGetTick(loopId)
        
        if active:
            # Start a note
            # Create a score event string for CSound
            score_event = 'i %d %f %f %f %f %f %f %f %f %f %f %f %d %d %d' % (
                int(params[0]),  # instrument number
                current_tick * self.tick_duration,  # start time (seconds)
                params[2] * self.tick_duration,  # duration (seconds)
                params[3],  # p4: pitch
                params[4],  # p5: amplitude
                params[5],  # p6: pan
                params[6],  # p7: reverb send
                params[7],  # p8: track ID
                params[8],  # p9: attack
                params[9],  # p10: decay
                params[10],  # p11: filter type
                params[11],  # p12: filter cutoff
                int(params[12]),  # p13: tied
                int(params[13]),  # p14: instrument ID
                int(params[14]) if len(params) > 14 else 0  # p15: instrument ID 2
            )
            self.cs.readScore(score_event)
        else:
            # Stop a note - in CSound, we can use a negative p3 to turn off a note
            score_event = 'i -%d %f 0' % (
                int(params[0]),  # instrument number (negative to turn off)
                current_tick * self.tick_duration  # start time (seconds)
            )
            self.cs.readScore(score_event)
            
        if Config.DEBUG > 2:
            print(f'DEBUG: loopPlay - active: {active}, note: {score_event}')

    def play(self, csnote, secs_per_tick, storage=_new_note_array()):
        a = self.csnote_to_array(csnote, storage)
        a[self.DURATION] = a[self.DURATION] * secs_per_tick
        a[self.ATTACK] = max(a[self.ATTACK]*a[self.DURATION], 0.002)
        a[self.DECAY] = max(a[self.DECAY]*a[self.DURATION], 0.002)
        
        # Create a score event string for CSound
        # Format: i p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 p11 p12 p13 p14 p15
        # p1: instrument number
        # p2: start time (0 = now)
        # p3: duration
        # p4-pN: instrument parameters
        score_event = 'i %d %f %f %f %f %f %f %f %f %f %f' % (
            int(a[self.INST_ID]),   # Instrument number
            0.0,                    # Start time (now)
            a[self.DURATION],       # Duration
            a[self.PITCH],          # Pitch
            a[self.AMPLITUDE],      # Amplitude
            a[self.PAN],            # Pan
            a[self.REVERBSEND],     # Reverb send
            a[self.ATTACK],         # Attack time
            a[self.DECAY],          # Decay time
            a[self.FILTERTYPE],     # Filter type
            a[self.FILTERCUTOFF]    # Filter cutoff
        )
        
        # Send the score event to CSound
        if hasattr(self, 'cs') and self.cs:
            self.cs.readScore(score_event)

    def csnote_to_array(self, csnote, storage):
        return self._csnote_to_array1(storage,
                csnote.onset,
                csnote.pitch,
                csnote.amplitude,
                csnote.pan,
                csnote.duration,
                csnote.trackId,
                csnote.attack,
                csnote.decay,
                csnote.reverbSend,
                csnote.filterType,
                csnote.filterCutoff,
                csnote.tied,
                csnote.instrumentId,
                csnote.mode,
                csnote.instrumentId2 )

    def _csnote_to_array1(self, storage, onset, pitch, amplitude, pan, duration,
            trackId, attack, decay, reverbSend, filterType, filterCutoff,
            tied, instrumentId, mode, instrumentId2 = -1):

        rval=storage
        instrument = self.instrumentDB.instId[instrumentId]

        if instrument.volatile != None:
            sound = os.path.join(Config.DATA_DIR, instrument.name)
            if os.path.isfile(sound):
                st_mtime = os.stat(sound).st_mtime
                if st_mtime != instrument.volatile:
                    instrument.volatile = st_mtime
                    loadedInstruments.remove(instrument.name)
                    self.load_instrument(instrument.name)
                    time.sleep(0.2)

        if instrument.kit != None:
            instrument = self.instrumentDB.instNamed[instrument.kit[pitch]]
            pitch = 1
            time_in_ticks = 0
        else:
            pitch = GenerationConstants.TRANSPOSE[ pitch - 24 ]
            time_in_ticks = 1

        instrument_id_offset = 0
        # condition for tied notes
        if instrument.csoundInstrumentId == Config.INST_TIED:
            if tied:
                if mode == 'mini':
                    duration = -1
                    instrument_id_offset = 0
                elif mode == 'edit':
                    instrument_id_offset = 0
                    if duration < 0:
                        duration = -1
            else:
                if mode == 'mini':
                    instrument_id_offset = 0
                elif mode == 'edit':
                    instrument_id_offset = 100

        if instrument.csoundInstrumentId == Config.INST_SIMP:
            if mode == 'mini':
                instrument_id_offset = 0
            elif mode == 'edit':
                if instrument.name[0:4] == 'drum':
                    instrument_id_offset = 0
                else:
                    instrument_id_offset = 100

        amplitude = amplitude / sqrt(pitch) * instrument.ampScale
        rval[0] = (instrument.csoundInstrumentId + \
                (trackId+1) + instrument_id_offset) + trackId * 0.01
        rval[1] = onset
        rval[2] = duration
        rval[3] = pitch
        rval[4] = reverbSend
        rval[5] = amplitude
        rval[6] = pan
        rval[7] = Config.INSTRUMENT_TABLE_OFFSET + instrument.instrumentId
        rval[8] = attack
        rval[9] = decay
        rval[10]= filterType
        rval[11]= filterCutoff
        rval[12]= float(instrument.loopStart)
        rval[13]= float(instrument.loopEnd)
        rval[14]= float(instrument.crossDur)

        if instrumentId2 != -1:
            instrument2 = self.instrumentDB.instId[instrumentId2]
            csInstrumentId2 = (instrument2.csoundInstrumentId + 100) * 0.0001
            rval[15] = Config.INSTRUMENT_TABLE_OFFSET + instrumentId2 + csInstrumentId2
            rval[16] = instrument2.loopStart
            rval[17] = instrument2.loopEnd
            rval[18] = instrument2.crossDur
        else:
            rval[15] = -1
            rval[16] = 0
            rval[17] = 0
            rval[18] = 0

        return rval

_Client = None

def new_csound_client():
    global _Client
    if _Client == None:
        _Client = _CSoundClientPlugin()
        _Client.connect(True)
        _Client.setMasterVolume(100.0)
        #_Client.load_instruments()
        time.sleep(0.2)
    return _Client
