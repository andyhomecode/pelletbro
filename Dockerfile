FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY petlibro.py main.py ./

EXPOSE 8077

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8077"]
