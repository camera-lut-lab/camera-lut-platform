# Camera LUT Platform

A cross-platform project for collecting, previewing, applying, and sharing camera LUTs. It demonstrates image processing, camera APIs, backend services, databases, and AI integration.

## Scope

- iOS camera app with live LUT preview and one-tap filter switching.
- Desktop web app for LUT collection, discovery, preview, and sharing.
- Java business API for accounts, works, sharing permissions, wallet ledger, and AI request relay.
- Python AI service for opt-in photo analysis and LUT recommendations through a China-accessible Qwen endpoint.
- C/C++ LUT core for parsing .cube files and applying 3D LUT interpolation across mobile and web.

External camera support is model-specific. Canon, Sony, and Nikon are initial adapter targets; Panasonic and Fujifilm are later targets. Each camera model must state its actual connection, transfer, registration, and in-camera switching capabilities.

## Architecture

    iOS app ─┐
    Web app ─┼─> Java API / wallet / AI relay ─> Python AI service ─> Qwen
    Android ─┘                 │
                               ├─ PostgreSQL
                               └─ S3-compatible object storage

    C: .cube parsing and validation
    C++: LUT sampling and interpolation
    C ABI: native mobile bridge
    WebAssembly: browser bridge

See docs/architecture.md for module boundaries, data flow, and delivery phases.

## Repository status

This repository contains public architecture notes and an initial Python AI service scaffold. The iOS app, web app, Java API, database schema, and C/C++ LUT core are planned modules and are not implemented here yet.

## Run the Python AI service

    cd python-ai
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    cd ..

Fill in .env locally with the Model Studio key, China-region endpoint, model name, and a long random internal service token. Never commit .env.

Start from repository root:

    set -a
    source python-ai/.env
    set +a
    uvicorn app.main:app --app-dir python-ai --host 127.0.0.1 --port 8001

The service accepts authenticated internal requests at POST /internal/v1/lut/recommendation and does not store uploaded photos. When analysis is requested, the selected image is sent to the configured Qwen provider for inference; disclose this in the product before upload. See python-ai/README.md.

## Public/private data boundary

This public repository contains source code and technical documentation only. Do not commit API keys, internal service tokens, private user details, real photos, account data, or private conversation records. Store credentials in environment variables or a secret manager. Private project notes belong in the private shared-memory repository.

## Model configuration

The AI service uses the OpenAI-compatible Chat Completions interface provided by Alibaba Cloud Model Studio. Configure the endpoint and model name for the selected China region and workspace; keep credentials server-side. See the official Qwen API documentation: https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions/

## License

No open-source license has been selected yet.
