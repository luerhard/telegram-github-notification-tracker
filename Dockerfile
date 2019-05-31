FROM python:3.7-alpine

COPY issuetracker/  setup.py main.py /app/

WORKDIR /app

RUN apk --no-cache add gcc \
                       libc-dev \
                       libffi-dev \
                       openssl-dev \
    && pip install --no-cache-dir . \
    && apk del gcc \
               libc-dev \
               libffi-dev \
               openssl-dev

COPY config.ini /app

CMD ["python", "main.py"]