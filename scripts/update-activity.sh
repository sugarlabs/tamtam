#!/bin/sh
DEST=/usr/share/activities/TamTam.activity
SRC=.
PYTHON_DIR=" . Jam Edit miniTamTam Util SynthLab Generation Resources "
OTHER_DIRS=" "
FILES="Util/Clooper/aclient.so Resources/crop.csd Resources/univorc.csd "
for DIR in $PYTHON_DIR ; do
    echo cp $SRC/$DIR/*.py $DEST/$DIR
    cp $SRC/$DIR/*.py $DEST/$DIR
done

for DIR in $OTHER_DIRS ; do
    echo cp -R $SRC/$DIR/* $DEST/$DIR
    cp -R $SRC/$DIR/* $DEST/$DIR
done

for F in $FILES ; do
    echo cp $F $DEST/$F
    cp $F $DEST/$F
done
