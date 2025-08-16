FROM python:3.13-alpine3.21

SHELL ["/bin/bash", "-c"]

RUN git clone https://github.com/roilevi01/MoneyBot.git
RUN cd MoneyBot

RUN apt-get update && apt-get install -y 
COPY  requirements.txt .
RUN pip install -r requirements.txt

ARG APP_ENV
ARG API_KEY
ENV APP_ENV=$APP_ENV
ENV API_KEY=$API_KEY
ENTRYPOINT [ "python3 main.py" ]
# test webhook