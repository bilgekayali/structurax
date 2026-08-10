FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir ".[demo]"

EXPOSE 7860
CMD ["python", "app.py"]
