<CsoundSynthesizer>
<CsOptions>
-+rtaudio=alsa -idevaudio -odevaudio -m0 -W -s -d -b128 -B512
</CsOptions>
<CsInstruments>
/*sr=22050*/
/*ksmps=50*/
sr=11025
ksmps=75
nchnls=2

gaudp1  init 0
gaudp2  init 0
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

opcode  control, k, i
iControlNum   xin

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
elseif iControlType == 2 then
kControl    randomi iPar1, iPar2, iPar3
elseif iControlType == 3 then
kControl    adsr    iPar1+.0001, iPar2, iPar3, iPar4
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
aSource	gbuzz	5000*kpara4, ipitch*kpara1, int(abs(kpara2))+5, 0, kpara3, 2
elseif iSourceType == 3 then
if iPar2 == 0 then 
imode = 0
elseif iPar2 == 1 then
imode = 10
elseif iPar2 == 2 then
imode = 12
endif
aSource vco2    2000*kpara4, ipitch*kpara1, imode, 0.1, 0, iPar3
elseif iSourceType == 4 then  
aSource pluck   5000*kpara4, ipitch*(abs(kpara1))+.001, 40, 0, 6
aSource butterlp    aSource, 5000
elseif iSourceType == 5 then
if int(iPar1) == 0 then
aSource rand   5000*kpara4
elseif int(iPar1) == 1 then
aSource pinkish 5000*kpara4
elseif int(iPar1) == 2 then
aSource gauss   5000*kpara4
endif
elseif iSourceType == 6 then
iSndpitch = p4/261.626
iPar2 = iPar2
p3      =   nsamp(5000+iPar2) * 0.000045351 / (iSndpitch*iPar1) 
aSource      loscil  kpara4*.4, iSndpitch*iPar1, 5000+iPar2, 1
aSource butterlp aSource, 5000
elseif iSourceType == 7 then
ivoy    =   int(iPar2)*3
iform1  table   ivoy, 4
iform2  table   ivoy+1, 4
iform3  table   ivoy+2, 4
kvibadev	randomi	-.0852, .0152, .5
kvibfdev	randomi	-.032, .032, .5
kvibfreqrand	randomi	4.5, 6, .2
kvibfatt    linseg  0, .3, 1, p3-.3, 1
kvib		oscili	(1+kvibadev)*kvibfatt, (kvibfreqrand+kvibfdev), 1
kharm		randomi	40, 50, 1.34
kmul		randomi	.80, .84, 1.45
kbam		randomi	480., 510., 2.07
kfunddev	randomi	-.0053, .0052, 1.05
ar  		gbuzz  	kbam, (p4*kpara1*(1+kfunddev)+kvib), int(kharm), 0, kmul, 2
a1 			resonx 	ar, iform1, 140, 2, 1 
a2 			resonx 	ar, iform2, 180, 2, 1 
a3 			resonx 	ar, iform3, 220, 2, 1 
aSource     = ((a1*80)+(a2*55)+(a3*40))*kpara4
endif

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
amod    oscili  kpara2, kpara1, 1
aFx = (as*amod)*kpara4
elseif iFxType == 5 then
ain =   as*kpara4
aLeft, aRight freeverb ain, ain, kpara1, kpara2, sr
aFx =   ((aLeft+aRight)*.707*kpara3)+(as*(1-kpara3))
elseif iFxType == 6 then
fsig  pvsanal   as, 1024, 256, 1024, 1 
ftps1  pvscale   fsig, kpara1
ftps2  pvscale   fsig, kpara2    
a1  pvsynth  ftps1
a2  pvsynth  ftps2
aFx = a1+a2
adry delay as, .04
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

ia	ftgen	89,	0, 64, -2, -1009, -1103, -1123, -1281, -1289, -1307, -1361, -1409, -1429, -1543, -1583, -1601, -1613, -1709, -1801, -1949, -2003, -2111, -2203, -2341, -2411, -2591, -2609, -2749, -2801, -2903, -3001, -3109, -3203, -3301, -3407, -3539, 0.82, 0.81,	0.8,	0.79, 0.78, 0.77, 0.76, 0.75, 0.74, 0.73, 0.72, 0.71, 0.7, 0.69, 0.68, 0.67, 0.66, 0.65, 0.64, 0.63, 0.62, 0.61, 0.6, 0.59, 0.58, 0.57, 0.56, 0.55, 0.54, 0.53, 0.52, 0.51

ib	ftgen	90,	0, 16, -2, -179, -223, -233, -311, -347, -409, -433, -509, 0.76, 0.74, 0.72, 0.7, 0.68, 0.64, 0.62, 0.6

ain		dcblock		gainrev*0.05	
arev	nreverb		ain, 2.8, 0.7, 0, 32, 89, 8, 90
arev	butterlp	arev, 5000
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
event "i", 5202, 0 , .5, itab 
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

ain = gasynth
itable = 5000 + p4
aindex line 0, p3,.25*p3
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

kc1     control     1
kc2     control     2
kc3     control     3
kc4     control     4

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

gasynth =   aout

        outs    aout, aout

aout = 0 
zacl	0, 8   
        
endin

/****************************************************************
Soundfile player with tied notes
****************************************************************/
instr 5999

gkptime times
gkrtime rtclock
giptime times
girtime rtclock
/*
giptime = i(gkptime)
girtime = i(gkrtime)
*/

endin

instr 5001

;ipit    =   p4
;irg     =   p5
;iamp = p6
;ipan    =   p7
;itab    =   p8
;iatt    =   p9
;idecay = p10
;ifiltType = p11 - 1
;icutoff = p12

idurfadein     init    0.005
idurfadeout     init    0.095
iampe0    	init    1                    ; FADE IN           
iampe1    	=  	p6				     ; SUSTAIN
iampe2    	init    1				     ; FADE OUT

itie     	tival                        ; VERIFIE SI LA NOTE EST LIEE 
if itie  ==  1     	igoto nofadein       ; SI NON "FADE IN"

idurfadein  init p9
iampe0    	init     0                   ; FADE IN
iskip   =   1 
kpitch     	init  	p4*3                 ; INIT FREQUENCE POUR LES NOTES NON-LIEES
kamp   init    p6
kpan        init    p7
krg         init    p5

nofadein:
iskip   =   0
igliss  =   0.005

if p3   < 	0       igoto nofadeout       ; VERIFIE SI LA NOTE EST TENUE, SI NON "FADE OUT"

idurfadeout     init    p10
iampe2      init    0                     ; FADE OUT

nofadeout:

idelta  =   idurfadein+idurfadeout
if idelta > abs(p3) then
idelta = abs(p3)
endif

iampe0      =       iampe0 * p6
iampe2      =       iampe2 * p6
kenv     	linseg  iampe0, idurfadein, iampe1, abs(p3)-idelta, iampe1, idurfadeout,  iampe2		; AMPLITUDE GLOBALE

; SI LA NOTE EST LIEE, ON SAUTE LE RESTE DE L'INITIALISATION
           	tigoto  tieskip

kpitch     	portk  	p4, igliss, p4    	             ; GLISSANDO
kpan        portk   p7, igliss, p7
krg         portk   p5, igliss, p5
kcutoff     portk   p12, igliss, p12

a1	     flooper2	1, kpitch, .25, .5, .1, p8, 0, 0, 0, iskip

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

ftfree 5000, 0
ftfree 5001, 0
ftfree 5002, 0
ftfree 5003, 0
ftfree 5004, 0
ftfree 5005, 0
ftfree 5006, 0
ftfree 5007, 0
ftfree 5008, 0
ftfree 5009, 0
ftfree 5010, 0
ftfree 5011, 0
ftfree 5012, 0
ftfree 5013, 0
ftfree 5014, 0
ftfree 5015, 0
ftfree 5016, 0
ftfree 5017, 0
ftfree 5018, 0
ftfree 5019, 0
ftfree 5020, 0
ftfree 5021, 0
ftfree 5022, 0
ftfree 5023, 0
ftfree 5024, 0
ftfree 5025, 0
ftfree 5026, 0
ftfree 5027, 0
ftfree 5028, 0
ftfree 5029, 0
ftfree 5030, 0
ftfree 5031, 0
ftfree 5032, 0
ftfree 5033, 0
ftfree 5034, 0
ftfree 5035, 0
ftfree 5036, 0
ftfree 5037, 0
ftfree 5038, 0
ftfree 5039, 0
ftfree 5040, 0
ftfree 5041, 0
ftfree 5042, 0
ftfree 5043, 0
ftfree 5044, 0
ftfree 5045, 0
ftfree 5046, 0
ftfree 5047, 0
ftfree 5048, 0
ftfree 5049, 0
ftfree 5050, 0
ftfree 5051, 0
ftfree 5052, 0
ftfree 5053, 0
ftfree 5054, 0
ftfree 5055, 0
ftfree 5056, 0
ftfree 5057, 0
ftfree 5058, 0
ftfree 5059, 0
ftfree 5060, 0
ftfree 5061, 0
ftfree 5062, 0
ftfree 5063, 0
ftfree 5064, 0
ftfree 5065, 0
ftfree 5066, 0
ftfree 5067, 0
ftfree 5068, 0
ftfree 5069, 0

endin


/********************************************************************
soundfile player for percussion - resonance notes
********************************************************************/
instr 5002

;p3      =   p3
;ipit    =   p4
;irg     =   p5
;iamp = p6
;ipan    =   p7
;itab    =   p8
;iatt    =   p9
;idecay = p10
;ifiltType = p11 - 1
;icutoff = p12

a1	 flooper2	1, p4*3, .25, .750, .2, p8

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

/***********************************************************************
Simple soundfile player
***********************************************************************/

instr 5777

iptime     = i(gkptime)
irtime     = i(gkrtime)
icurptime  = iptime - giptime
icurlag    = irtime - iptime - (girtime - giptime)
i2         =  p5 - (irtime - girtime) + 0.1
/* print i2, p5, irtime */
event_i "i", p4, i2, p6, p7, p8, p9, p10, p11, p12, p13, p14

endin

instr 5003

;ipit    =   p4
;irg     =   p5
;iamp = p6
;ipan    =   p7
;itab    =   p8
p3      =   nsamp(p8) * 0.0000625 / p4
;iatt    =   p9
;idecay = p10
;ifiltType = p11-1
;icutoff = p12

a1      loscil  p6, p4*3, p8, 1

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

/******************************************************************** 
soundfile simple crossfade player 
********************************************************************/
instr 5004

ipit    =   p4
irg     =   p5
iamp = p6
ipan    =   p7
itab    =   p8
iatt    =   p9
idecay = p10

a1	 flooper2    1, ipit, .25, .750, .2, itab
a2      =   a1

kenv   adsr     iatt, 0.05, .8, idecay

gaoutL = a1*kenv*iamp*(1-ipan)+gaoutL
gaoutR = a2*kenv*iamp*ipan+gaoutR

gainrev	=       (a1+a2)*irg*kenv*.5*iamp+gainrev

endin 


/********************************************************************* 
simple karplus-strong plucked string 
*********************************************************************/
instr 5005

p3      =   p3+1
ipit    =   p4
irg     =   p5
iamp = p6
ipan    =   p7
itab    =   p8
iatt    =   p9
idecay = p10

icps    = 261.626 * ipit

a1      pluck   20000, icps, icps, 0, 5, .495, .495
a1      butterlp a1, 4000
a2      =   a1

kenv   adsr     iatt, 0.05, .8, idecay

gaoutL = a1*kenv*iamp*(1-ipan)+gaoutL
gaoutR = a2*kenv*iamp*ipan+gaoutR

gainrev =	    (a1+a2)*irg*kenv*.5*iamp+gainrev

endin 

/********************************************************************** 
FM synth instrument 
**********************************************************************/
instr 5006

ipit    =   p4
irg     =   p5
iamp = p6
ipan    =   p7
itab    =   p8
iatt    =   p9
idecay = p10

kModDev randomi 0.995, 1.005, .45
kFondDev    randomi 0.9962, 1.0029, .93
kvibrato    vibrato .5, 5, 0.08, 0.5, 3, 5, 3, 5, 1

iImin   =   2
iImax   =   4
iamp    =   3000
kfond   =   261.626 * ipit * kFondDev + kvibrato
kformant    =   800
kPortFreq   =   kfond * 3
kModFreq    =   kfond * 2 * kModDev
kModFreq2   =   kfond * 2.001 * kModDev
kPortFreq2  =   int((kformant/kPortFreq) + 0.5) * kfond

kenv1   expseg  0.001, .05, iamp, p3 - .15, iamp, .1, 0.001 
kenv2   oscil1i  0, kModFreq*(iImax-iImin), p3, 44

amod    oscili  iImin*kModFreq+kenv2, kModFreq, 1
amod2   oscili  iImin*kModFreq2+kenv2, kModFreq2, 1 

aport1  oscili  kenv1, kPortFreq+amod+amod2, 1
aport2  oscili  kenv1*0.5, kPortFreq2+(amod*0.33), 1

a1    =   aport1+aport2
a2      =   a1

kenv   adsr     iatt, 0.05, .8, idecay

gaoutL = a1*kenv*iamp*(1-ipan)+gaoutL
gaoutR = a2*kenv*iamp*ipan+gaoutR

gainrev =	    (a1+a2)*irg*kenv*iamp+gainrev

    endin

/********************************************************************** 
Waveshaping instrument 
**********************************************************************/
instr 5007

ipit    =   p4 * 261.626
irg     =   p5
iamp = p6
ipan    =   p7
itab    =   p8
iatt    =   p9
idecay = p10

kvib	vibr	2, 5, 53
kamp	line	.42, p3, .1
kampdev	randi	.07, .5, .666

asig	oscili	kamp+kampdev, ipit+kvib, 50

a1	table	asig, 51, 1, .5
a1  balance a1, asig
a1 = a1*10000
a2      delay   a1, .041

kenv   adsr     iatt, 0.05, .8, idecay

gaoutL = a1*kenv*iamp*(1-ipan)+gaoutL
gaoutR = a2*kenv*iamp*ipan+gaoutR

gainrev =	    (a1+a2)*irg*kenv*iamp+gainrev

endin


/**************************************************************************
 General Soundfile Player - Used by Memosono
**************************************************************************/


instr 108
/* soundfile play control
  p4 : filename
  p5 : unique instance ID
  p6 : output gain (0-1)
  p7 : udp send gain (0-1)
  p8 : offset in seconds

  channels:
  sfplay.<ID>.on  - instance control channel (1:on 0: off)
  sfplay.<ID>.gain - soundfile play gain (0-1)
  sfplay.<ID>.udpgain - udp send gain (0-1)
  sfplay.<ID>.flen  - holds the channel length
*/
S1 strget p4
inst = p5
ich    filenchnls S1
iln    filelen  S1
ioffset = p8

Slen  sprintf "sfplay.%d.flen", p5  ; file length channel
chnset iln, Slen

if ioffset >= iln then
turnoff
else
iln = iln - ioffset
endif

Splay sprintf "sfplay.%d.on", inst  ; instance control channel
Sname sprintf "sfplay.%d.fname", inst  ; filename channel
Sgain sprintf "sfplay.%d.gain", inst ; gain channel
Sudp  sprintf "sfplay.%d.udpgain", inst ; udp gain channel  
chnset S1, Sname
chnset 1,  Splay
chnset p6, Sgain
chnset p7, Sudp
event_i "i",109,0,iln,inst,ich,ioffset
turnoff
endin


instr 109
/* soundfile player
  This is the actual soundfile player.
  It never gets called directly
*/
ich = p5
inst= p4
ioffset = p6
Splay sprintf "sfplay.%d.on", inst  ; instance control channel
Sname sprintf "sfplay.%d.fname", inst  ; filename channel
Sgain sprintf "sfplay.%d.gain", inst ; gain channel
Sudp  sprintf "sfplay.%d.udpgain", inst ; udp gain channel   
kon chnget Splay
kg1 chnget Sgain
kg2 chnget Sudp
S1  chnget Sname
if kon == 0 then
printf "sfplay:%d OFF\n", 1, inst
turnoff
endif
if ich = 1 then
a1 diskin2 S1,1,ioffset,1
a2 = a1
else
a1,a2 diskin2 S1,1,ioffset,1
endif
     outs a1*kg1, a2*kg1
gaudp1 = a1*kg2 + gaudp1
gaudp2 = a2*kg2 + gaudp2
printf_i "sfplay:%d\n", 1, inst
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
f2 0 8192 11 1 1

f4 0 64 -2 	250 2250 2980 		420 2050 2630 		590 1770 2580
				750 1450 2590		290 750 2300		360 770 2530		
				520 900 2510		710 1230 2700		250 1750 2160		
				350 1350 2250		500 1330 2370		570 1560 2560		
				600 1470 2770		500 1280 2660		580 1090 2960

f40 0 1024 10 1 0  .5 0 0 .3  0 0 .2 0 .1 0 0 0 0 .2 0 0 0 .05 0 0 0 0 .03 ; ADDITIVE SYNTHESIS WAVE
f41 0 8193 19 .5 .5 270 .5 ; SIGMOID FUNCTION
f44 0 8192 5 1 8192 0.001 ; EXPONENTIAL FUNCTION

i256 0 600000
i200 0 600000

</CsScore>
</CsoundSynthesizer>
