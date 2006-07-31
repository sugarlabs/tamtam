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
gainrev init 0

/*****************************************************************
Reverb
*****************************************************************/
instr 200

ia	ftgen	89,	0, 64, -2, -1009, -1103, -1123, -1281, -1289, -1307, -1361, -1409, -1429, -1543, -1583, -1601, -1613, -1709, -1801, -1949, -2003, -2111, -2203, -2341, -2411, -2591, -2609, -2749, -2801, -2903, -3001, -3109, -3203, -3301, -3407, -3539, 0.82, 0.81,	0.8,	0.79, 0.78, 0.77, 0.76, 0.75, 0.74, 0.73, 0.72, 0.71, 0.7, 0.69, 0.68, 0.67, 0.66, 0.65, 0.64, 0.63, 0.62, 0.61, 0.6, 0.59, 0.58, 0.57, 0.56, 0.55, 0.54, 0.53, 0.52, 0.51

ib	ftgen	90,	0, 16, -2, -179, -223, -233, -311, -347, -409, -433, -509, 0.76, 0.74, 0.72, 0.7, 0.68, 0.64, 0.62, 0.6

ain		dcblock		gainrev*0.1	
arev	nreverb		ain, 2.5, 0.7, 0, 32, 89, 8, 90
arev	butterlp	arev, 5000
arev	butterlp	arev, 5000

		outs		arev, arev
		
		gainrev	=	0
		
endin

/****************************************************************
Soundfile player with tied notes
****************************************************************/
instr 101

ipit    =   p4
igain   =   p5
irg     =   p6
itab    =   p7
inotegain = p8
ipan    =   p9

iampe0    	init    1                    ; FADE IN           
iampe1    	init  	1				     ; SUSTAIN
iampe2    	init    1				     ; FADE OUT

itie     	tival                        ; VERIFIE SI LA NOTE EST LIEE 
if itie  ==  1     	igoto nofadein       ; SI NON "FADE IN"

iampe0    	init     0                   ; FADE IN
iskip   =   1 
kpitch     	init  	ipit                 ; INIT FREQUENCE POUR LES NOTES NON-LIEES
kgain       init    igain
knotegain   init    inotegain
kpan        init    ipan
krg         init    irg

nofadein:
iskip   =   0
igliss  =   0.015

if p3   < 	0       igoto nofadeout       ; VERIFIE SI LA NOTE EST TENUE, SI NON "FADE OUT"
iampe2      init    0                     ; FADE OUT

nofadeout:

kenv     	linseg  iampe0, 0.002, iampe1, abs(p3)-0.1, iampe1, 0.098,  iampe2		; AMPLITUDE GLOBALE

; SI LA NOTE EST LIEE, ON SAUTE LE RESTE DE L'INITIALISATION
           	tigoto  tieskip

kpitch     	portk  	ipit, igliss, ipit    	             ; GLISSANDO
kgain       portk   igain, igliss, igain
knotegain   portk   inotegain, igliss, inotegain
kpan        portk   ipan, igliss, ipan
krg         portk   irg, igliss, irg

a1	     flooper2	1, kpitch, .25, .750, .2, itab, 0, 0, 0, iskip
a2      =   a1

        outs        a1*kgain*kenv*knotegain*(1-kpan), a2*kgain*kenv*knotegain*kpan

gainrev	=	        (a1+a2)*krg*kenv*.5*inotegain+gainrev

tieskip:                                       
endin

/********************************************************************
soundfile player for percussion - resonance notes
********************************************************************/
instr 102

p3      =   p3+3
ipit    =   p4
igain   =   p5
irg     =   p6
itab    =   p7
inotegain = p8
ipan    =   p9

a1	 flooper2	1, ipit, .25, .750, .2, itab
a2      =   a1

kenv    expseg  0.001, .003, .4, p3 - .003, 0.001

        outs    a1*igain*kenv*inotegain*(1-ipan), a2*igain*kenv*inotegain*ipan

gainrev	=	    (a1+a2)*irg*kenv*.5*inotegain+gainrev

endin 

/***********************************************************************
Simple soundfile player
***********************************************************************/
instr 103

ipit    =   p4
igain   =   p5
irg     =   p6
itab    =   p7
inotegain = p8
ipan    =   p9

a1      loscil  1, ipit, itab, 1
a2      =   a1

kenv    linen   1, 0.001, p3, 0.01
        outs    a1*igain*kenv*inotegain*(1-ipan), a2*igain*kenv*inotegain*ipan

gainrev =	    (a1+a2)*irg*kenv*.5*inotegain+gainrev

endin 

/******************************************************************** 
soundfile simple crossfade player 
********************************************************************/
instr 104

ipit    =   p4
igain   =   p5
irg     =   p6
itab    =   p7
inotegain = p8
ipan    =   p9

a1	 flooper2    1, ipit, .25, .750, .2, itab
a2      =   a1

kenv    linen   .4, 0.002, p3, 0.01

        outs    a1*igain*kenv*inotegain*(1-ipan), a2*igain*kenv*inotegain*ipan

gainrev	=       (a1+a2)*irg*kenv*.5*inotegain+gainrev

endin 


/********************************************************************* 
simple karplus-strong plucked string 
*********************************************************************/
instr 105

p3      =   p3+3
ipit    =   p4
igain   =   p5
irg     =   p6
itab    =   p7
inotegain = p8
ipan    =   p9

; 130.813
icps    = 261.626 * ipit

a1      pluck   20000, icps, icps, 0, 5, .495, .495
a1      butterlp a1, 4000
a2      =   a1

kenv    linen   1, 0.001, p3, 0.01
        outs    a1*igain*kenv*inotegain*(1-ipan), a2*igain*kenv*inotegain*ipan

gainrev =	    (a1+a2)*irg*kenv*.5*inotegain+gainrev

endin 

/**************************************************************************
UDP receiver
**************************************************************************/
instr 256
gaudp1 = 0
gaudp2 = 0
a1 = 0
outs a1, a1
endin 

</CsInstruments>
<CsScore>
f1 0 8192 10 1
f40 0 1024 10 1 0  .5 0 0 .3  0 0 .2 0 .1 0 0 0 0 .2 0 0 0 .05 0 0 0 0 .03 ; ADDITIVE SYNTHESIS WAVE
f41 0 8193 19 .5 .5 270 .5 ; SIGMOID FUNCTION
;f42 0 256 1 "/home/olipet/TamTam/instruments/marmstk1.wav" 0 0 0
;f43 0 256 1 "/home/olipet/TamTam/instruments/impuls20.wav" 0 0 0
f44 0 8192 5 1 8192 0.001

i256 0 600000
i200 0 600000

</CsScore>
</CsoundSynthesizer>
