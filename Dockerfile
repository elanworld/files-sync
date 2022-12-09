FROM python:3.8.0-alpine
WORKDIR /app
RUN apk add cifs-utils
RUN apk add -U tzdata
ADD . .
RUN echo  $'import py_compile\n\
import sys\n\
py_compile.compile(sys.argv[1], cfile=f"{sys.argv[1]}c")\n' > build.py
RUN find . -name '*.py' -type f -print -exec python build.py {} \;
RUN find . -name '*.py' -type f -print -exec rm {} \;
RUN echo  $'\
set -e \n\
mkdir $SMBPATH -p && mkdir $SMBPATH1 -p \n\
if [ -n $SMBURL ]; then \n\
    mount -t cifs -o username="$SMBUSER",password="$SMBPASSWORD",iocharset=utf8 $SMBURL $SMBPATH \n\
fi \n\
if [ -n $SMBURL1 ]; then \n\
    mount -t cifs -o username="$SMBUSER1",password="$SMBPASSWORD1",iocharset=utf8 $SMBURL1 $SMBPATH1 \n\
fi \n\
python -u files_sync.pyc $SMBPATH $SMBPATH1 $ARGV \n\
' > entrypiont.sh
RUN chmod 777 entrypiont.sh
CMD ./entrypiont.sh