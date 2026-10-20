# Architecture

## Goals

- Provide an iOS shooting experience with responsive live LUT switching.
- Provide a desktop web library for collecting, organizing, previewing, generating, and sharing LUTs.
- Keep shared business rules and wallet accounting in the Java service.
- Keep model-provider credentials on the server.
- Reuse one C/C++ LUT implementation across mobile and web where practical.
- Describe external camera support by exact model and tested capability.

## System layout

    iOS (Swift/SwiftUI) ───────┐
    Desktop web (Vue/TS) ──────┼─> Java API (Spring Boot)
    Future Android ────────────┘       ├─ account and permissions
                                       ├─ LUT library and sharing
                                       ├─ wallet ledger and sandbox recharge
                                       └─ internal AI relay
                                               │
                                               v
                                        Python AI (FastAPI)
                                               │
                                               v
                                            Qwen API

    PostgreSQL: accounts, LUT metadata, sharing rules, ledger, task state
    S3-compatible storage: user photos, LUT files, rendered previews

    C: .cube parsing and validation
    C++: 3D LUT lookup, interpolation, image transform
    C ABI: native mobile bridge
    WebAssembly: browser bridge

## Modules

### iOS shooting app

- Swift, SwiftUI, AVFoundation, Core Image, and Metal.
- Camera preview, still capture, local photo selection, live filter selection, and export.
- Request photo analysis only after the user chooses an image and starts the operation.
- Keep an unfiltered original available where the user chooses to retain it.

### Shared LUT core

- C parses and validates .cube headers, dimensions, domains, and RGB triples.
- C++ implements LUT sampling and interpolation with a stable C ABI.
- Expose the same deterministic implementation to iOS and WebAssembly.
- Reject malformed files with clear errors and bounded allocations.

### Desktop web app

- Vue 3, TypeScript, and Vite.
- LUT collection, search, metadata, permission management, sharing links, and before/after preview.
- WebAssembly handles LUT math; WebGL2 can accelerate preview rendering.

### Java business API

- Java 21, Spring Boot, Spring Security, and versioned REST APIs.
- Owns accounts, works, sharing permissions, wallet ledger, upload authorization, and AI task state.
- Authenticates users and reserves credits before sending an internal request to Python.
- Settles actual usage on success and releases the reservation on provider failure.
- Keeps the Qwen API key and the Java-to-Python service token on the server.

### Python AI service

- Python, FastAPI, and the OpenAI-compatible Qwen API.
- Accepts internal requests only; it is not exposed directly to mobile or browser clients.
- Performs opt-in scene analysis and returns structured recommendation data.
- Does not claim that model output is a finished .cube file. Deterministic image-processing code creates and validates LUT output.

### Storage

- PostgreSQL stores relational records and task state.
- S3-compatible object storage stores image and LUT binaries.
- Local development may use MinIO. Do not store binary files directly in PostgreSQL.

## AI request flow

1. The user selects a photo and requests analysis.
2. The client uploads it to the Java API using an authorized upload flow.
3. Java validates identity, permission, quota, and wallet balance, then reserves credits.
4. Java calls the internal Python endpoint.
5. Python validates the image and calls the configured China-region Qwen endpoint.
6. Python returns structured scene tags, recommendation rationale, and suggested parameters.
7. Java records usage and settles or releases reserved credits, then returns the result to the client.

For style imitation, request both a reference style image and a target image. For more accurate color transformation fitting, use aligned original/graded image pairs. A single image can support scene and style recommendations but cannot reveal an exact grading transform.

## External camera adapters

Start with Canon, Sony, and Nikon adapters. Panasonic and Fujifilm are later targets. Each camera model needs an explicit capability record for:

- discovery and wireless connection;
- photo transfer;
- LUT file transfer;
- in-camera LUT registration;
- in-camera LUT switching.

Do not infer support for every model from a brand-level SDK or another model's feature. Keep unsupported capabilities visible in the UI.

## Delivery phases

1. Core experience: iOS capture and live LUT preview, web LUT library, Java API, Python/Qwen relay, and sandbox wallet.
2. Camera adapters: add model-specific Canon, Sony, and Nikon paths and validate them on actual hardware.
3. Expansion: Android, mini program, Panasonic, Fujifilm, and photo-style generation agent.

## Acceptance areas

- Reject malformed and oversized LUT files.
- Confirm preview and exported image use the same LUT implementation.
- Enforce private, unlisted-link, and public work permissions.
- Test wallet insufficient balance, model timeout, settlement, and refund paths.
- Validate image upload, analysis output, and user-visible errors.
- Test camera disconnect and unsupported model capabilities.

## Public data boundary

Keep credentials, internal service tokens, user photos, account information, and private conversation records out of this public repository. Store personal or sensitive project notes in the private shared-memory repository.
