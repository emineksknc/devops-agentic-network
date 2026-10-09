FROM node:22-slim AS web
WORKDIR /web
COPY frontend-react/package.json frontend-react/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend-react/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY --from=web /web/dist ./frontend-react/dist

EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
