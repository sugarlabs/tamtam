
yum install vim-common vim-enhanced screen git-core

echo 'please ensure your ssh key is in place, then type your git-repo username: '

read USER

mkdir cvs
cd cvs
git-clone "git+ssh://$USER@dev.laptop.org/git/projects/tamtam" tamtam


echo 'edit olpc's .xinitrc file to change the window-manager'
