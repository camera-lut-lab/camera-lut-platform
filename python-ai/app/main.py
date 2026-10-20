import base64
import hmac
import io
import json
import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from openai import AsyncOpenAI
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError


load_dotenv()

MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

SERVICE_TOKEN = os.environ["AI_INTERNAL_TOKEN"]
MODEL_API_KEY = os.environ["DASHSCOPE_API_KEY"]
MODEL_BASE_URL = os.environ["QWEN_BASE_URL"]
MODEL_NAME = os.environ["QWEN_MODEL"]

client = AsyncOpenAI(
    api_key=MODEL_API_KEY,
    base_url=MODEL_BASE_URL,
    timeout=60.0,
    max_retries=1,
)

app = FastAPI(title="Camera LUT AI Service", version="0.1.0")


class LUTRecommendation(BaseModel):
    scene_tags: list[str] = Field(default_factory=list)
    mood: str
    lighting: str
    contrast: str
    palette: list[str] = Field(default_factory=list)
    recommended_style: str
    explanation: str
    suggested_parameters: dict[str, float] = Field(default_factory=dict)
    cautions: list[str] = Field(default_factory=list)


async def require_internal_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def validate_image(data: bytes, content_type: str | None) -> tuple[str, int, int]:
    if not data:
        raise HTTPException(status_code=400, detail="Image is empty")

    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 12 MB limit")

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()

        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            detected_type = Image.MIME.get(image.format or "")

    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid image file")

    if detected_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image format")

    return detected_type, width, height


def parse_model_json(content: str) -> LUTRecommendation:
    try:
        payload = json.loads(content)
        return LUTRecommendation.model_validate(payload)
    except (json.JSONDecodeError, ValidationError):
        raise HTTPException(
            status_code=502,
            detail="AI service returned an invalid recommendation",
        )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/internal/v1/lut/recommendation",
    response_model=LUTRecommendation,
    dependencies=[Depends(require_internal_token)],
)
async def recommend_lut(
    image: Annotated[UploadFile, File()],
    language: str = "zh-CN",
) -> LUTRecommendation:
    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    content_type, width, height = validate_image(image_bytes, image.content_type)

    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    image_url = f"data:{content_type};base64,{encoded_image}"

    system_prompt = """
你是摄影调色分析助手。分析用户主动提交的照片，给出可解释的 LUT 风格推荐。
只输出一个 JSON 对象，字段必须为：
scene_tags: 字符串数组
mood: 字符串
lighting: 字符串
contrast: 字符串
palette: 颜色十六进制字符串数组
recommended_style: 字符串
explanation: 字符串
suggested_parameters: 数值字典，数值范围 0 到 1
cautions: 字符串数组

不要声称已经生成 .cube 文件。建议参数只是供后续确定性图像算法使用的初始值。
不要识别或推断照片中人物的身份、敏感属性或精确位置。
"""

    user_prompt = (
        f"请用 {language} 回答。照片尺寸为 {width}×{height}。"
        "分析画面的场景、光线、色彩和适合的调色风格。"
        "参数建议限定为 exposure、contrast、saturation、warmth、fade。"
    )

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception:
        # Do not return provider errors, request headers, or credentials to clients.
        raise HTTPException(status_code=502, detail="AI provider request failed")

    content = response.choices[0].message.content
    if not content:
        raise HTTPException(status_code=502, detail="AI provider returned no result")

    return parse_model_json(content)
