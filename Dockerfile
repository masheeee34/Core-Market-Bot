FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libffi-dev build-essential && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data && chown -R user:user /app

USER user

EXPOSE 7860

CMD ["python", "main.py"]
