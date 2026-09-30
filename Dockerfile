FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip wheel --no-cache-dir --wheel-dir /wheels --no-deps . \
    && pip wheel --no-cache-dir --wheel-dir /wheels \
        "fastapi>=0.110,<0.120" "uvicorn[standard]>=0.27" \
        "scikit-learn>=1.4" "pydantic>=2.6" "pandas>=2.2" \
        "numpy>=1.26" "requests>=2.31"

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels \
        "fastapi>=0.110,<0.120" "uvicorn[standard]>=0.27" \
        "scikit-learn>=1.4" "pydantic>=2.6" "pandas>=2.2" \
        "numpy>=1.26" "requests>=2.31" \
    && pip install --no-cache-dir --no-index --no-deps \
        --find-links=/wheels fraudpulse \
    && rm -rf /wheels

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
