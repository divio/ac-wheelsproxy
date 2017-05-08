FROM aldryn/base:py3-3.23
RUN mkdir -p /app
RUN pipsi install tox
WORKDIR /app
ADD requirements.txt /app/
RUN pip install --use-wheel --no-deps -r requirements.txt
ADD ./ /app/
EXPOSE 80
ENV DJANGO_SETTINGS_MODULE settings
RUN sh -c '. /app/.env.collectstatic && /app/manage.py collectstatic --noinput'
CMD start web
