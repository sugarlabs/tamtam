 #!/bin/sh
 
for F in $( git-status | grep modified | cut -f 2 | cut -d ' ' -f 4 ) ; do
    git-update-index $F 
done
