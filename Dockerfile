FROM python:alpine
COPY requirements.txt .
RUN pwd; \
    apk add --update;\
    apk --no-cache --update-cache; \
    apk add python3-dev build-base git; \
    # ln -s /usr/include/locale.h /usr/include/xlocale.h;\
    python3 -m pip install -u pip setuptools; \
    # pip install autopep8 requests flake8 bandit openpyxl google-api-python-client google-auth-httplib2 google-auth-oauthlib;
    pip install -r requirements.txt;