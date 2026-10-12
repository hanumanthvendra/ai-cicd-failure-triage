FROM python:3.12-slim
WORKDIR /app
COPY reqirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["python", "-m", "app"]
