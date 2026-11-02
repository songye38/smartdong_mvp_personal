import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.services.video_renderer import render_video

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["render"],
)


class RenderRequest(BaseModel):
    job_id: str
    edit_plan: dict[str, Any]
    subtitle_scenes: list[dict[str, Any]]


@router.post("/render")
def create_video(request: RenderRequest):
    try:
        result = render_video(
            job_id=request.job_id,
            edit_plan=request.edit_plan,
            subtitle_scenes=request.subtitle_scenes,
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
        logger.exception("영상 렌더링 실패")

        raise HTTPException(
            status_code=500,
            detail="영상 렌더링 중 오류가 발생했습니다.",
        )