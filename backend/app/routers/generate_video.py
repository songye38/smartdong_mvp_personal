import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.video_orchestrator import generate_video
from app.services.project_store import load_project

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["video-generation"],
)


class GenerateVideoRequest(BaseModel):
    url: str = Field(min_length=1)


@router.post("/generate-video")
def create_video(request: GenerateVideoRequest):
    try:
        result = generate_video(request.url)

        return {
            "success": True,
            "data": result,
        }

    except Exception as error:
        logger.exception("통합 영상 생성 실패")

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    try:
        project = load_project(job_id)

        return {
            "success": True,
            "data": project,
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="작업을 찾을 수 없습니다.",
        )