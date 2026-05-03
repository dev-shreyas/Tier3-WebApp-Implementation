FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

ARG BUILD_NUMBER=local
ARG GIT_COMMIT=unknown

ENV BUILD_NUMBER=${BUILD_NUMBER} \
    GIT_COMMIT=${GIT_COMMIT} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --from=builder /install /usr/local

COPY app.py .

COPY templates ./templates
COPY static ./static

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 7003

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7003/health')"

CMD ["python", "app.py", "-m", "gunicorn", "--bind", "0.0.0.0:7003", "--workers", "2", "app:app"]
