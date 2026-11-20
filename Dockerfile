# Multi-stage, non-root runtime image shared by the API, UI, and MCP services.
FROM python:3.11-slim AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt ./requirements.txt
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/opspilot/.cache/huggingface \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
WORKDIR /app
RUN groupadd --system opspilot && useradd --system --gid opspilot --create-home opspilot \
    && mkdir -p /app/data/uploads /app/data/vector_store /app/data/workflows /home/opspilot/.cache/huggingface \
    && chown -R opspilot:opspilot /app/data /home/opspilot
COPY --from=dependencies /install /usr/local
COPY --chown=opspilot:opspilot . /app
USER opspilot
EXPOSE 8000 8501
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
