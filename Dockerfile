FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py queryagent.py tools.py config.py ./
COPY anon.db ./
COPY templates/ ./templates/

EXPOSE 5000

CMD ["python3", "app.py"]
