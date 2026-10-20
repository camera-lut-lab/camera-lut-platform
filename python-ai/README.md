# Python AI service

This FastAPI service is an internal component called by the Java business API. Do not expose it directly to mobile or browser clients.

## Configure

From the repository root:

    cd python-ai
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    cd ..

Edit .env locally:

- AI_INTERNAL_TOKEN: a long random secret shared only with the Java backend.
- DASHSCOPE_API_KEY: your Model Studio key. Do not commit it.
- QWEN_BASE_URL: the OpenAI-compatible endpoint for your Model Studio region and workspace.
- QWEN_MODEL: a vision-capable model available in that workspace.

Start the service from the repository root:

    set -a
    source python-ai/.env
    set +a
    uvicorn app.main:app --app-dir python-ai --host 127.0.0.1 --port 8001

## Endpoints

- GET /healthz
- POST /internal/v1/lut/recommendation: multipart form with image and optional language; requires Authorization: Bearer <AI_INTERNAL_TOKEN>.

The service keeps the uploaded image in memory for the request and does not write it to disk. For inference, it forwards the selected image to the configured Qwen provider; the product should disclose this before upload. The Java API should validate the user and wallet balance before calling this endpoint.

## Local request example

    curl -X POST http://127.0.0.1:8001/internal/v1/lut/recommendation \
      -H "Authorization: Bearer $AI_INTERNAL_TOKEN" \
      -F "image=@/path/to/photo.jpg" \
      -F "language=zh-CN"
