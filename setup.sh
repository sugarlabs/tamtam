make -C common/Util/Clooper
python TamTamEdit.activity/setup.py dist
python TamTamMini.activity/setup.py dist
python TamTamSynthLab.activity/setup.py dist
mv TamTam*/*.xo .
