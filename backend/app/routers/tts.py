import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.tts_generator import generate_tts

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["tts"],
)


class TTSScene(BaseModel):
    scene_id: str
    narration: str
    images: list[str] = Field(default_factory=list)


class TTSRequest(BaseModel):
    scenes: list[TTSScene]


@router.post("/tts")
def create_tts(request: TTSRequest):
    try:
        result = generate_tts(
            [scene.model_dump() for scene in request.scenes]
        )

        return {
            "success": True,
            "data": result,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        logger.exception("TTS 생성 실패")

        raise HTTPException(
            status_code=500,
            detail="음성 생성 중 오류가 발생했습니다.",
        )