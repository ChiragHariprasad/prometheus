FROM python:3.12-slim

RUN pip install --no-cache-dir "setuptools>=68.0,<70" mlflow==2.15.1 psycopg2-binary boto3

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)" || exit 1

CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} \
    --default-artifact-root ${MLFLOW_ARTIFACT_ROOT} \
    --workers 4
