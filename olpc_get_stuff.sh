
yum install vim-common vim-enhanced screen git-core fluxbox ctags

echo 'please ensure your ssh key is in place, then type your git-repo username: '
echo 'copy over .vim* from somewhere'
echo 'export GIT_AUTHOR_NAME GIT_COMMITTER_NAME in .bashrc'
echo 'edit olpc's .xinitrc file to change the window-manager'

read USER

mkdir cvs
cd cvs
git-clone "git+ssh://$USER@dev.laptop.org/git/projects/tamtam" tamtam


