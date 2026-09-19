FROM python:3.12-slim

WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY samples/ ./samples/
COPY scripts/ ./scripts/
RUN mkdir -p /srv/data/projects

ENV CAER_DATA_DIR=/srv/data CAER_SAMPLES_DIR=/srv/samples
WORKDIR /srv/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
