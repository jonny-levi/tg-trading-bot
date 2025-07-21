FROM python:3.13-alpine3.21
RUN git clone https://github.com/your-username/MoneyBot.git
RUN cd MoneyBot
RUN apt-get update && apt-get install -y \
    bash \
    Copy \ 
    Edit 
COPY  requirements.txt .
RUN pip install -r requirements.txt

ARG APP_ENV
ARG API_KEY
ENV APP_ENV=$APP_ENV
ENV API_KEY=$API_KEY