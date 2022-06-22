FROM python:3.8.0-alpine
WORKDIR /app
RUN apk add util-linux
ADD . .
RUN echo  $'import py_compile\n\
import sys\n\
py_compile.compile(sys.argv[1], cfile=f"{sys.argv[1]}c")\n' > build.py
RUN find . -name '*.py' -type f -print -exec python build.py {} \;
RUN find . -name '*.py' -type f -print -exec rm {} \;
RUN echo  $'\
mkdir $SMBPATH -p && mkdir $SMBPATH1 -p \n\
mount -t cifs -o username="$SMBUSER",password="$SMBPASSWORD",iocharset=utf8 $SMBURL $SMBPATH \n\
mount -t cifs -o username="$SMBUSER1",password="$SMBPASSWORD1",iocharset=utf8 $SMBURL1 $SMBPATH1 \n\
python -u files_sync.pyc $SMBPATH $SMBPATH1 \n\
' > entrypiont.sh
RUN chmod 777 entrypiont.sh
CMD ./entrypiont.sh