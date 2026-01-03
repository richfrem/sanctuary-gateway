FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn sse-starlette

COPY server.py .

EXPOSE 8005

CMD ["python", "server.py"]
