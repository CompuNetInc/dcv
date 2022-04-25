FROM python:3.9.7-slim-bullseye

WORKDIR /app
COPY . .

RUN pip install -e .

ENTRYPOINT ["dcv"]