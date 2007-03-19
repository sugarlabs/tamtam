#!/bin/sh
mkdir tmp
cd tmp
wget http://www.studioimaginaire.com/~tamtam/rpm/rpms-olpc-gcc-stuff.zip
wget http://www.studioimaginaire.com/~tamtam/rpm/rpms-olpc-vim-git.zip
unzip rpms-olpc-gcc-stuff.zip
unzip rpms-olpc-vim-git.zip
mv rpms-olpc-gcc-stuff/*.rpm .
mv rpms-olpc-vim-git/*.rpm .
rpm -i *.rpm

