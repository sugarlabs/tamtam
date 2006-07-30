<CsoundSynthesizer>
<CsOptions>
-odevaudio -+rtaudio=alsa -m0 -d -b256 -B2048 
</CsOptions>

<CsInstruments>
sr=44100
ksmps=100
nchnls=2

gaudp1  init 0
gaudp2  init 0

;#include "/home/sean/Projects/TamTam/Sound/reverb"
;#include "basic.instruments"
;#include "/home/sean/Projects/TamTam/Sound/addSynth"
;#include "/home/sean/Projects/TamTam/Sound/sfplayer4"

;instr 254
;/* udp receive instrument 
;   p4 : unique instance ID

;  channels:
;   osc.<ID>.on  - instance control (1: on, 0: off)
;*/
;ion = 1
;inst = 0
;Son   sprintf  "udprecv.%d.on"  , inst  ; instance control channel
;chnset ion, Son
;kon   chnget  Son

;if kon == 0 then
;printf "udprecv:%d OFF\n", 1, inst
;turnoff
;endif

;asig sockrecv 40001, 32
;outs asig, asig 
;endin 


;instr 255
;/* udp send instrument */
;socksends gaudp1, gaudp2, "1.1.25.90", 40000, 256     
;endin

instr 256
gaudp1 = 0
gaudp2 = 0
a1 = 0
outs a1, a1
;kres    active  106
;printk  0.5, kres
endin 

</CsInstruments>

<CsScore>
f1 0 1024 10 1
f40 0 1024 10 1 0  .5 0 0 .3  0 0 .2 0 .1 0 0 0 0 .2 0 0 0 .05 0 0 0 0 .03
;f34 0 262144 -1 "/home/olipet/Sons/gam1" 0 1 0
i256 0 600000
i200 0 600000

</CsScore>
</CsoundSynthesizer>
