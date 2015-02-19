FROM debian:jessie
MAINTAINER Nadrieril "nadrieril@eleves.polytechnique.fr"

#ENV HTTP_PROXY http://kuzh.polytechnique.fr:8080
#ENV http_proxy http://kuzh.polytechnique.fr:8080
#ENV https_proxy http://kuzh.polytechnique.fr:8080

RUN apt-get update && \
    apt-get install -y python-pip gunicorn python-dev libmysqlclient-dev python-dateutil

RUN mkdir /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install -r requirements.txt

ADD . /app/
RUN sed -i 's/bars_django\.settings\.dev_local/bars_django.settings.prod/' bars_django/wsgi.py && \
    sed -i 's/bars_django\.settings\.dev_local/bars_django.settings.prod/' manage.py && \
    echo yes | python manage.py collectstatic

VOLUME /srv/server
CMD rm -r /srv/server/*; \
    cp -R /app/static /srv/server/static; \
    python manage.py migrate; \
    gunicorn bars_django.wsgi -w 4 -b unix:/srv/server/gunicorn.sock --log-level=debug