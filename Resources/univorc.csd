<CsoundSynthesizer>
<CsOptions>
-+rtaudio=alsa -idevaudio -odevaudio -m0 -W -s -d -b128 -B512
</CsOptions>
<CsInstruments>
sr=16000
ksmps=64
nchnls=2
giScale = 1/sr

gainrev init 0
gaoutL init 0
gaoutR init 0
gasynth init 0

/*****************************
matrix for TamTam's SynthLab
*****************************/
zakinit 8, 32

/*****************************
opcodes needed by TamTam's SynthLab
*****************************/
opcode  ControlMatrice, i, iikkkk
iTable, iIndex, kc1, kc2, kc3, kc4  xin

iSomme table iIndex, iTable+3

if iSomme == 0 then
goto noparams
endif

iPar table iIndex, iTable

if iSomme == 1 then
kp = iPar
elseif iSomme == 3 then
kp = iPar * kc1
elseif iSomme == 5 then
kp = iPar * kc2
elseif iSomme == 7 then
kp = iPar * kc1 * kc2
elseif iSomme == 9 then
kp = iPar * kc3
elseif iSomme == 11 then
kp = iPar * kc1 * kc3
elseif iSomme == 13 then
kp = iPar * kc2 * kc3
elseif iSomme == 15 then
kp = iPar * kc1 * kc2 * kc3
elseif iSomme == 17 then
kp = iPar * kc4
elseif iSomme == 19 then
kp = iPar * kc1 * kc4
elseif iSomme == 21 then
kp = iPar * kc2 * kc4
elseif iSomme == 23 then
kp = iPar * kc1 * kc2 * kc4
elseif iSomme == 25 then
kp = iPar * kc3 * kc4
elseif iSomme == 27 then
kp = iPar * kc1 * kc3 * kc4
elseif iSomme == 29 then
kp = iPar * kc2 * kc3 * kc4
elseif iSomme == 31 then
kp = iPar * kc1 * kc2 * kc3 * kc4
endif

if iTable == 5201 then
zkw     kp, iIndex+1
elseif iTable == 5202 then
zkw     kp, iIndex+17
endif

xout    iIndex

noparams:
endop

opcode  SourceMatrice, i, iaaaa
iIndex, as1, as2, as3, as4  xin

iSomme table iIndex-1, 5206

if iSomme == 0 then
goto noparams
endif

if iSomme == 1 then
as = as1
elseif iSomme == 2 then
as = as2
elseif iSomme == 3 then
as = as1 + as2
elseif iSomme == 4 then
as = as3
elseif iSomme == 5 then
as = as1 + as3
elseif iSomme == 6 then
as = as2 + as3
elseif iSomme == 7 then
as = as1 + as2 + as3
elseif iSomme == 8 then
as = as4
elseif iSomme == 9 then
as = as1 + as4
elseif iSomme == 10 then
as = as2 + as4
elseif iSomme == 11 then
as = as1 + as2 + as4
elseif iSomme == 12 then
as = as3 + as4
elseif iSomme == 13 then
as = as1 + as3 + as4
elseif iSomme == 14 then
as = as2 + as3 + as4
elseif iSomme == 15 then
as = as1 + as2 + as3 + as4
endif

zaw     as, iIndex
xout    iIndex

noparams:
endop

opcode  FxMatrice, i, iaaaa
iIndex, as1, as2, as3, as4  xin

iSomme table iIndex-1, 5206

if iSomme == 0 then
goto noparams
endif

if iSomme == 1 then
as = as1
elseif iSomme == 2 then
as = as2
elseif iSomme == 3 then
as = as1 + as2
elseif iSomme == 4 then
as = as3
elseif iSomme == 5 then
as = as1 + as3
elseif iSomme == 6 then
as = as2 + as3
elseif iSomme == 7 then
as = as1 + as2 + as3
elseif iSomme == 8 then
as = as4
elseif iSomme == 9 then
as = as1 + as4
elseif iSomme == 10 then
as = as2 + as4
elseif iSomme == 11 then
as = as1 + as2 + as4
elseif iSomme == 12 then
as = as3 + as4
elseif iSomme == 13 then
as = as1 + as3 + as4
elseif iSomme == 14 then
as = as2 + as3 + as4
endif

zaw     as, iIndex
xout    iIndex

noparams:
endop

opcode  control, k, ii
iControlNum, idur   xin

iControlType table  iControlNum-1, 5203

if iControlType == 0 then
goto nocontrol
endif

ioffset = (iControlNum-1)*4
iPar1   table   ioffset, 5200
iPar2   table   ioffset+1, 5200
iPar3   table   ioffset+2, 5200
iPar4   table   ioffset+3, 5200

if iControlType == 1 then
kControl    lfo     iPar1, iPar2, int(iPar3)
kControl    =       kControl+iPar4
elseif iControlType == 2 then
irange      =       (iPar2-iPar1)*.5
kControl    randi   irange, iPar3, iPar4-.001, 0, irange+iPar1 
elseif iControlType == 3 then
kControl    adsr    iPar1+.0001*idur, iPar2*idur, iPar3, iPar4*idur
endif

xout    kControl

nocontrol:
endop   

opcode  source, a, ii
iSourceNum, ipitch     xin

iSourceType table iSourceNum+3, 5203

if iSourceType == 0 then
goto nosource
endif

ioffset =   (iSourceNum-1)*4
kpara1  zkr ioffset+1
kpara2  zkr ioffset+2
kpara3  zkr ioffset+3
kpara4  zkr ioffset+4

iPar1   table   ioffset, 5201
iPar2   table   ioffset+1, 5201
iPar3   table   ioffset+2, 5201
iPar4   table   ioffset+3, 5201

if iSourceType == 1 then
aSource	foscil	2000*kpara4, ipitch, kpara1, kpara2, kpara3, 1
elseif iSourceType == 2 then
aSource	gbuzz	5000*kpara4, ipitch*kpara1, int(abs(kpara2))+5, 0, kpara3+0.01, 2
elseif iSourceType == 3 then
iPar2 = int(iPar2)
if iPar2 == 0 then 
imode = 0
elseif iPar2 == 1 then
imode = 10
elseif iPar2 == 2 then
imode = 12
endif
aSource vco2    2000*kpara4, ipitch*kpara1, imode, 0.1, 0, iPar3
elseif iSourceType == 4 then  
if iPar3 == 0 then
kvib = 0
goto novib
else
kvibenv    linseg  0, .3, 1, p3-.3, 1
kvib    oscil	ipitch*.015, kpara3, 1
endif
novib:
aSource pluck   5000*kpara4, ipitch*(abs(kpara1))+.001+kvib, 40, 0, 6
aSource butterlp    aSource, kpara2
elseif iSourceType == 5 then
if int(iPar1) == 0 then
ar rand   5000*kpara4
elseif int(iPar1) == 1 then
ar pinkish 5000*kpara4
elseif int(iPar1) == 2 then
ar gauss   5000*kpara4
endif
aSource butterbp ar, kpara2, kpara3
aSource balance aSource, ar
elseif iSourceType == 6 then
iSndpitch = p4/261.626
iPar2 = iPar2
p3      =   nsamp(5000+iPar2) * giScale / (iSndpitch*iPar1) 
aSource      loscil  kpara4*.4, iSndpitch*kpara1, 5000+iPar2, 1
aSource butterlp aSource, kpara3
elseif iSourceType == 7 then
kvoy    =  int(kpara2*3)
kform1  table   kvoy, 4
kform2  table   kvoy+1, 4
kform3  table   kvoy+2, 4
kform1  port    kform1, .1, 500
kform2  port    kform2, .1, 1500
kform3  port    kform3, .1, 2500
kvibadev	randomi	-.0852, .0152, .5
kvibfdev	randomi	-.032, .032, .5
kvibfreqrand	randomi	kpara3-.75, kpara3+.75, .2
kvibfatt    linseg  0, .3, 1, p3-.3, 1
kvib		oscili	(1+kvibadev)*kvibfatt, (kvibfreqrand+kvibfdev), 1
kharm		randomi	40, 50, 1.34
kmul		randomi	.80, .84, 1.45
kbam		randomi	480., 510., 2.07
kfunddev	randomi	-.0053, .0052, 1.05
ar  		gbuzz  	kbam, (p4*kpara1*(1+kfunddev)+kvib), int(kharm), 0, kmul, 2
a1 			resonx 	ar, kform1, 140, 2, 1 
a2 			resonx 	ar, kform2, 180, 2, 1 
a3 			resonx 	ar, kform3, 220, 2 , 1 
aSource     = ((a1*80)+(a2*55)+(a3*40))*kpara4
endif

aSource dcblock aSource
xout    aSource

nosource:
endop

opcode  effects, a, ii
iFxNum, ipitch     xin

iFxType table iFxNum+7, 5203

if iFxType == 0 then
goto nofx
endif

as1  zar iFxNum
as2  zar iFxNum+4
as  =   as1+as2

ioffset =   (iFxNum+3)*4
kpara1  zkr ioffset+1
kpara2  zkr ioffset+2
kpara3  zkr ioffset+3
kpara4  zkr ioffset+4

ioffset2 =   (iFxNum-1)*4
iPar1   table   ioffset2, 5202
iPar2   table   ioffset2+1, 5202
iPar3   table   ioffset2+2, 5202
iPar4   table   ioffset2+3, 5202

if iFxType == 1 then
aFx	wguide1	as, abs(kpara1)+1, kpara2, kpara3
aFx	=		aFx*kpara4
elseif iFxType == 2 then
aFx	lpf18	as*.0005, abs(kpara1)+20, kpara2, kpara3
aFx	=		aFx*5000*kpara4
elseif iFxType == 3 then
aFx bqrez   as*kpara4, abs(kpara1)+20, abs(kpara2)+1, int(iPar3)
aFx balance aFx, as*kpara4
elseif iFxType == 4 then
;amod    oscili  kpara2, kpara1, 1
amod lfo kpara2, kpara1, int(iPar3)
aFx = (as*amod)*kpara4
elseif iFxType == 5 then
ain =   as*kpara4
arev reverb ain, kpara1
arev butterlp arev, kpara2
aFx =   (arev*kpara3)+(as*(1-kpara3))
elseif iFxType == 6 then
fsig  pvsanal   as, 1024, 256, 1024, 1 
ftps1  pvscale   fsig, kpara1
aFx  pvsynth  ftps1
adry delay as, iPar2
aFx = ((aFx*kpara3)+(adry*(1-kpara3)))*kpara4                    
endif

xout    aFx

nofx:
endop

/****************************************************************
Reverb + master out
*****************************************************************/
instr 200

gktime timek
koutGain chnget "masterVolume"
koutGain = koutGain * 0.01
gkduck  init    1
gkduck port gkduck, .03, 1. 

ain		dcblock		gainrev*0.05	
arev	reverb		ain, 2.5
arev	butterlp	arev, 5000
	
		outs		(arev + gaoutL)*koutGain*gkduck, (arev + gaoutR) * koutGain*gkduck

        gaoutL = 0
        gaoutR = 0		
		gainrev	=	0
		
endin

/****************************************************************
Handler audio input recording
****************************************************************/
instr 5201

ktim timeinsts 

gkduck = .05
itab = p4
ain inch 1
krms    rms     ain
ktrig   trigger     krms, 3000, 0

if ktrig == 1 then
event "i", 5202, 0 , 1, itab 
turnoff
endif

ithresh = p3 - .5
if ktim > ithresh then
gkduck = 1
turnoff
endif

endin


/****************************************************************
Audio input recording
****************************************************************/
instr 5202

gkduck  linseg .05, .4, .05, .1, 1
ain inch 1

adel    delay   ain, .01

itable = 5000 + p4
aindex line 0, p3, 1
kenv   adsr     0.005, 0.05, .9, 0.01
tabw  adel*kenv, aindex, itable, 1
endin

/****************************************************************
SynthLab input recording
****************************************************************/
instr 5204

ain = gasynth*4
itable = 5000 + p4
itabdur = ftlen(itable)
print itabdur
;aindex line 0, p3,.25*p3
aindex phasor .25
tabw  ain, aindex, itable, 1
gasynth = 0
endin

/************************
TamTam's SynthLab instrument
************************/
instr 5203

aSource1	init	0
aSource2	init	0
aSource3	init	0
aSource4	init	0
aFx1		init	0
aFx2		init	0
aFx3		init	0
aFx4		init	0
aout		init	0

ipitch  =   p4

kc1     control     1,p3
kc2     control     2,p3
kc3     control     3,p3
kc4     control     4,p3

is1p1   ControlMatrice     5201, 0, kc1, kc2, kc3, kc4
is1p2   ControlMatrice     5201, 1, kc1, kc2, kc3, kc4
is1p3   ControlMatrice     5201, 2, kc1, kc2, kc3, kc4
is1p4   ControlMatrice     5201, 3, kc1, kc2, kc3, kc4
is2p1   ControlMatrice     5201, 4, kc1, kc2, kc3, kc4
is2p2   ControlMatrice     5201, 5, kc1, kc2, kc3, kc4
is2p3   ControlMatrice     5201, 6, kc1, kc2, kc3, kc4
is2p4   ControlMatrice     5201, 7, kc1, kc2, kc3, kc4
is3p1   ControlMatrice     5201, 8, kc1, kc2, kc3, kc4
is3p2   ControlMatrice     5201, 9, kc1, kc2, kc3, kc4
is3p3   ControlMatrice     5201, 10, kc1, kc2, kc3, kc4
is3p4   ControlMatrice     5201, 11, kc1, kc2, kc3, kc4
is4p1   ControlMatrice     5201, 12, kc1, kc2, kc3, kc4
is4p2   ControlMatrice     5201, 13, kc1, kc2, kc3, kc4
is4p3   ControlMatrice     5201, 14, kc1, kc2, kc3, kc4
is4p4   ControlMatrice     5201, 15, kc1, kc2, kc3, kc4

aSource1    source  1, ipitch*2
aSource2    source  2, ipitch*2
aSource3    source  3, ipitch*2
aSource4    source  4, ipitch*2

ifx1p1   ControlMatrice     5202, 0, kc1, kc2, kc3, kc4
ifx1p2   ControlMatrice     5202, 1, kc1, kc2, kc3, kc4
ifx1p3   ControlMatrice     5202, 2, kc1, kc2, kc3, kc4
ifx1p4   ControlMatrice     5202, 3, kc1, kc2, kc3, kc4
ifx2p1   ControlMatrice     5202, 4, kc1, kc2, kc3, kc4
ifx2p2   ControlMatrice     5202, 5, kc1, kc2, kc3, kc4
ifx2p3   ControlMatrice     5202, 6, kc1, kc2, kc3, kc4
ifx2p4   ControlMatrice     5202, 7, kc1, kc2, kc3, kc4
ifx3p1   ControlMatrice     5202, 8, kc1, kc2, kc3, kc4
ifx3p2   ControlMatrice     5202, 9, kc1, kc2, kc3, kc4
ifx3p3   ControlMatrice     5202, 10, kc1, kc2, kc3, kc4
ifx3p4   ControlMatrice     5202, 11, kc1, kc2, kc3, kc4
ifx4p1   ControlMatrice     5202, 12, kc1, kc2, kc3, kc4
ifx4p2   ControlMatrice     5202, 13, kc1, kc2, kc3, kc4
ifx4p3   ControlMatrice     5202, 14, kc1, kc2, kc3, kc4
ifx4p4   ControlMatrice     5202, 15, kc1, kc2, kc3, kc4

ifx1in   SourceMatrice	    1, aSource1, aSource2, aSource3, aSource4
ifx2in   SourceMatrice	    2, aSource1, aSource2, aSource3, aSource4
ifx3in   SourceMatrice	    3, aSource1, aSource2, aSource3, aSource4
ifx4in   SourceMatrice	    4, aSource1, aSource2, aSource3, aSource4

ifx1in1  FxMatrice          5, aFx1, aFx2, aFx3, aFx4
ifx2in1  FxMatrice          6, aFx1, aFx2, aFx3, aFx4
ifx3in1  FxMatrice          7, aFx1, aFx2, aFx3, aFx4
ifx4in1  FxMatrice          8, aFx1, aFx2, aFx3, aFx4

aFx1	   effects		    1, ipitch
aFx2	   effects		    2, ipitch
aFx3	   effects		    3, ipitch
aFx4	   effects		    4, ipitch

iSourceOut1 table 8, 5206
iSourceOut2 table 9, 5206
iSourceOut3 table 10, 5206
iSourceOut4 table 11, 5206
iFxOut1 table 12, 5206
iFxOut2 table 13, 5206
iFxOut3 table 14, 5206
iFxOut4 table 15, 5206

aout    =   (aSource1*iSourceOut1)+(aSource2*iSourceOut2)+(aSource3*iSourceOut3)+(aSource4*iSourceOut4)+(aFx1*iFxOut1)+(aFx2*iFxOut2)+(aFx3*iFxOut3)+(aFx4*iFxOut4)

kenv adsr p5*p3, p6*p3, p7, p8*p3
aout = aout*kenv

gasynth =   aout

        outs    aout, aout

;aout = 0 
zacl	0, 8   
        
endin

/****************************************************************
Soundfile player with tied notes
****************************************************************/
instr 5999

/* gkptime times */
gkrtime rtclock
/* giptime times */
girtime rtclock

endin
/*************************
pitch, reverbGain, amp, pan, table, att, dec, filtType, cutoff, loopstart, loopend, crossdur
*************************/
instr 5001

idurfadein     init    0.005
idurfadeout     init    0.095
iampe0    	init    1                      
iampe1    	=  	p6
iampe2    	init    1

itie     	tival   
if itie  ==  1     	igoto nofadein   

idurfadein  init p9
iampe0    	init     0      
iskip   =   1 
kpitch     	init  	p4 
kamp   init    p6
kpan        init    p7
krg         init    p5

nofadein:
iskip   =   0
igliss  =   0.005

if p3   < 	0       igoto nofadeout  

idurfadeout     init    p10
iampe2      init    0    

nofadeout:

idelta  =   idurfadein+idurfadeout
if idelta > abs(p3) then
idelta = abs(p3)
endif

iampe0      =       iampe0 * p6
iampe2      =       iampe2 * p6
kenv     	linseg  iampe0, idurfadein, iampe1, abs(p3)-idelta, iampe1, idurfadeout,  iampe2

           	tigoto  tieskip

kpitch     	portk  	p4, igliss, p4 
kpan        portk   p7, igliss, p7
krg         portk   p5, igliss, p5
kcutoff     portk   p12, igliss, p12
kls	    portk   p13, igliss, p13
kle	    portk   p14, igliss, p14
kcd         portk   p15, igliss, p15

a1	     flooper2	1, kpitch, kls, kle, kcd, p8, 0, 0, 0, iskip

if (p11-1) != -1 then
acomp   =  a1
a1      bqrez   a1, kcutoff, 6, p11-1
a1      balance     a1, acomp
endif

a1      =   a1*kenv

gaoutL = a1*(1-kpan)+gaoutL
gaoutR =  a1*kpan+gaoutR

gainrev	=	        a1*krg+gainrev

  tieskip:                                    
endin

/***********************
DELETE RESOURCES
************************/

instr 5000

icount init 0

again:
ftfree 5000+icount, 0
icount = icount+1

if icount < p4 goto again

turnoff

endin

/********************************************************************
soundfile player for percussion - resonance notes
********************************************************************/
instr 5002

a1	 flooper2	1, p4, .25, .750, .2, p8

if (p11-1) != -1 then
acomp   =   a1
a1      bqrez   a1, p12, 6, p11-1 
a1      balance     a1, acomp
endif

kenv    expseg  0.001, .003, .6, p3 - .003, 0.001
klocalenv   adsr     p8, 0.05, .8, p10

a1      =   a1*kenv*klocalenv

gaoutL = a1*(1-p7)+gaoutL
gaoutR = a1*p7+gaoutR

gainrev	=	    a1*p5+gainrev

endin 

/**************************************************************
Simple soundfile player
**************************************************************/

instr 5777

/*iptime     = i(gkptime) */
irtime     = i(gkrtime)
/*icurptime  = iptime - giptime */
/*icurlag    = irtime - iptime - (girtime - giptime) */
i2         =  p5 - (irtime - girtime) + 0.1

event_i "i", p4, i2, p6, p7, p8, p9, p10, p11, p12, p13, p14

endin

instr 5003

p3      =   nsamp(p8) * giScale / p4

a1      loscil  p6, p4, p8, 1

if (p11-1) != -1 then
acomp = a1
a1      bqrez   a1, p12, 6, p11-1 
a1      balance     a1, acomp
endif

kenv   adsr     p9, 0.05, .8, p10

a1  =   a1*kenv

gaoutL = a1*(1-p7)+gaoutL
gaoutR = a1*p7+gaoutR

gainrev =	    a1*p5+gainrev

endin 

</CsInstruments>
<CsScore>
f1 0 8192 10 1
f2 0 8192 11 1 1

f4 0 32 -2 	250 2250 2980 	420 2050 2630 	590 1770 2580
		750 1450 2590	290 750 2300	360 770 2530			     520 900 2510    710 1230 2700   570 1560 2560			  0 0 0 0 0 

f40 0 1024 10 1 0  .5 0 0 .3  0 0 .2 0 .1 0 0 0 0 .2 0 0 0 .05 0 0 0 0 .03 ; ADDITIVE SYNTHESIS WAVE
f41 0 8193 19 .5 .5 270 .5 ; SIGMOID FUNCTION
f44 0 8192 5 1 8192 0.001 ; EXPONENTIAL FUNCTION

i200 0 600000

</CsScore>
</CsoundSynthesizer>
