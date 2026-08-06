FROM python:3.12-slim

WORKDIR /app

COPY back/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY back ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
