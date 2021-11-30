FROM python:3.7-slim
RUN pip3 install fastapi uvicorn requests unidecode 
EXPOSE 8092
COPY ./app /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8092"]