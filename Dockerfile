FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
COPY ml ./ml
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /install /usr/local
COPY app ./app
COPY ml ./ml

# Bake a trained model artifact into the image so container startup is fast
# and reproducible (retrain any time with `make train`).
RUN python -m ml.train

RUN useradd --create-home --uid 1000 fraudpulse \
    && chown -R fraudpulse:fraudpulse /app
USER fraudpulse

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
