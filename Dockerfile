FROM aldryn/base:2.2
RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app/
RUN pip install --use-wheel --no-deps -r requirements.txt
ADD ./ /app/
EXPOSE 80
ENV DJANGO_SETTINGS_MODULE settings
CMD start web
