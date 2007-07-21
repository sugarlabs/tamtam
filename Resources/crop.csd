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

asig diskin "/home/olpc/.sugar/default/tamtam/snds/tempMic.wav", 1
gasig dcblock asig

endin

/****************************************************************
Crop silence at the beginning
****************************************************************/
instr 2
ktimer timeinstk
ain = gasig
krms    rms     ain
if ktimer > 40 then
    ktrig   trigger     krms, 1500, 0
    if ktrig == 1 then
        event "i", 3, 0, 2
        event "i", 4, 2, 0.01
        turnoff
    endif
endif
endin

/****************************************************************
recording
****************************************************************/
instr 3
kenv   adsr     0.01, 0.05, .9, 0.01

adel    delay   gasig, .005

ihandle fiopen "/home/olpc/.sugar/default/tamtam/snds/micTemp", 2

fout "/home/olpc/.sugar/default/tamtam/snds/micTemp", 2, adel*kenv

;out adel*kenv
adel = 0
endin

/****************************************************************
Audio input recording ( closing file )
****************************************************************/
instr 4
ficlose "/home/olpc/.sugar/default/tamtam/snds/micTemp"
endin


</CsInstruments>

<CsScore>
f1 0 8192 10 1
i1 0 4
i2 0 4
</CsScore>

</CsoundSynthesizer>
