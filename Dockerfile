FROM python:alpine
RUN apk add --update;\
    apk --no-cache --update-cache; \
    # add python3-dev build-base; \
    ln -s /usr/include/locale.h /usr/include/xlocale.h;\
    pip install -r requirements.txt;