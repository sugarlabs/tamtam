
#NEED_FOR_SURE='vim-common vim-enhanced screen git-core ctags sox irssi diffutils'
#ALTERNATE_WM='xterm fluxbox'
GCC_STUFF='gcc make python-devel gcc-c++ csound-devel swig'

yum install $NEED_FOR_SURE $ALTERNATE_WM $GCC_STUFF

if [ ! -f ~/.Xdefaults ] ; then
    #use a legible xterm font
    echo 'xterm*font: -*-*-*-*-*-*-20-*-*-*-*-*-*-*' > ~/.Xdefaults
fi

echo 'please ensure your ssh key is in place, then type your git-repo username: '
echo 'copy over .vim* from somewhere'
echo 'export GIT_AUTHOR_NAME GIT_COMMITTER_NAME in .bashrc'
echo 'edit olpc's .xinitrc file to change the window-manager'


echo 'this might help you get your git repo back up:'
echo 'read USER'
echo 'mkdir cvs'
echo 'cd cvs'
echo 'git-clone "git+ssh://$USER@dev.laptop.org/git/projects/tamtam" tamtam'


