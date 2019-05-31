FROM python:3.7-alpine

COPY issuetracker/ /app/issuetracker
COPY setup.py main.py /app/

WORKDIR /app

RUN apk --no-cache add gcc \
                       libc-dev \
                       libffi-dev \
                       openssl-dev \

RUN pip install --no-cache-dir python-telegram-bot==11.1.0 pygithub==1.43.7

RUN pip install --no-cache-dir . \

COPY config.ini /app

CMD ["python", "main.py"]
