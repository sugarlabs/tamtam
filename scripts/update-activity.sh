#!/bin/sh
DEST=/usr/share/activities/TamTam.activity
SRC=.
PYTHON_DIR=" . Edit miniTamTam Util SynthLab Generation "
OTHER_DIRS=" Resources "
FILES="Util/Clooper/aclient.so"
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
