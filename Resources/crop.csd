<CsoundSynthesizer>

<CsOptions> 
-W -d -n
</CsOptions>

<CsInstruments>

sr=16000
ksmps=64
nchnls=1

/****************************************************************
Playing temp file
****************************************************************/
instr 1 

asig diskin "/home/olpc/.sugar/default/tamtam/tempMic.wav", 1
gasig = asig * 0.5

endin

/****************************************************************
Crop silence at the beginning
****************************************************************/
instr 2

itab = 1
ain = gasig
krms    rms     ain
ktrig   trigger     krms, 2000, 0

if ktrig == 1 then
event "i", 3, 0, 1
event "i", 4, 1, 0.01 
turnoff
endif
endin

/****************************************************************
recording
****************************************************************/
instr 3
kenv   adsr     0.005, 0.05, .9, 0.01

adel    delay   gasig, .01

ihandle fiopen "/home/olpc/.sugar/default/tamtam/micTemp", 2

fout "/home/olpc/.sugar/default/tamtam/micTemp", 2, adel*kenv

out adel*kenv
adel = 0
endin

/****************************************************************
Audio input recording ( closing file )
****************************************************************/
instr 4
ficlose "/home/olpc/.sugar/default/tamtam/micTemp"
endin


</CsInstruments>

<CsScore>
f1 0 8192 10 1
i1 0 4
i2 0 4
</CsScore>

</CsoundSynthesizer>
