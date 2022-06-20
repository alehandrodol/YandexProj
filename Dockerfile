FROM python:3.10.5-alpine

COPY . .

RUN pip install -r requirements.txt

EXPOSE 80

WORKDIR MegaMarket/

CMD uvicorn main:app --reload --host 0.0.0.0 --port 80