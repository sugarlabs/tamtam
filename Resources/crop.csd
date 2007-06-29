<CsoundSynthesizer>

<CsOptions>
-o /home/olpc/.sugar/tamtam/mic1 -W -d 
</CsOptions>

<CsInstruments>

sr=16000
ksmps=64
nchnls=1

/****************************************************************
Playing temp file
****************************************************************/
instr 1 

gasig diskin "/home/olpc/.sugar/default/tamtam/tempMic.wav, 1

endin

/****************************************************************
Crop silence at the beginning
****************************************************************/
instr 2

itab = 1
gain = gasig
krms    rms     gain
ktrig   trigger     krms, 1500, 0

;if ktrig == 1 then
event "i", 5, 0 , 4, itab 
;turnoff
;endif


instr 5
kenv   adsr     0.005, 0.05, .9, 0.01

adel    delay   gain, .01

out adel*kenv
adel = 0
endin


/****************************************************************
Audio input recording
****************************************************************/
instr 3
kenv   adsr     0.005, 0.05, .9, 0.01

adel    delay   gain, .01

Sname sprintf "/home/olpc/.sugar/default/tamtam/mic%d", int(p4)-6
ihandle fiopen Sname, 2
event "i", 4, 1 , .01, p4

fout Sname, 2, adel*kenv
adel = 0
endin

/****************************************************************
Audio input recording ( closing file )
****************************************************************/
instr 4
Sname sprintf "/home/olpc/.sugar/default/tamtam/mic%d", int(p4)-6
ficlose Sname
endin

</CsInstruments>

<CsScore>
f1 0 8192 10 1
i1 0 4
i2 0 4
</CsScore>

</CsoundSynthesizer>
