import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.subtitle_generator import generate_subtitles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["subtitles"])


class SubtitleScene(BaseModel):
    scene_id: str
    narration: str
    duration: float


class SubtitleRequest(BaseModel):
    job_id: str
    scenes: list[SubtitleScene]


@router.post("/subtitles")
def create_subtitles(request: SubtitleRequest):
    try:
        result = generate_subtitles(
            job_id=request.job_id,
            scenes=[scene.model_dump() for scene in request.scenes],
        )

        return {
            "success": True,
            "data": result,
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        logger.exception("자막 생성 실패")
        raise HTTPException(
            status_code=500,
            detail="자막 생성 중 오류가 발생했습니다.",
        )