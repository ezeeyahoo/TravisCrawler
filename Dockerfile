FROM python:alpine
COPY requirements.txt .
RUN  \
    apk add --update;\
    apk --no-cache --update-cache; \
    apk add python3-dev build-base git; \
    python3 -m pip install -u pip setuptools; \
    pip install -r requirements.txt;
