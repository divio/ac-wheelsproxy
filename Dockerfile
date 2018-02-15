FROM divio/base:4.4-py3.6-alpine3.6
ENV WHEELSPROXY_URL=https://wheels.aldryn.net/v1/pypi/$WHEELS_PLATFORM/ \
    PIP_INDEX_URL=https://wheels.aldryn.net/v1/pypi/$WHEELS_PLATFORM/+simple/
RUN pipsi install tox
COPY requirements.* /app/
RUN pip-reqs resolve && \
    pip install \
        --no-index \
        --no-deps \
        --requirement requirements.urls
COPY ./ /app/
EXPOSE 80
ENV DJANGO_SETTINGS_MODULE settings
RUN sh -c '. /app/.env.collectstatic && /app/manage.py collectstatic --noinput'
CMD start web
