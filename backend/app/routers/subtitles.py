import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.subtitle_generator import align_subtitles
from app.services.project_store import load_project, update_project

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
        # 1. 저장된 프로젝트 불러오기
        project = load_project(request.job_id)

        if not project:
            raise ValueError(
                "해당 프로젝트를 찾을 수 없습니다."
            )

        # 2. 스타일이 확정된 자막 가져오기
        styled_subtitles = project.get(
            "styled_subtitles"
        )

        if not styled_subtitles:
            raise ValueError(
                "스타일 자막이 없습니다. "
                "먼저 자막 스타일 생성 단계를 실행해 주세요."
            )

        # 3. TTS 음성과 자막 타이밍 정렬
        result = align_subtitles(
            job_id=request.job_id,
            scenes=[
                scene.model_dump()
                for scene in request.scenes
            ],
            styled_subtitles=styled_subtitles,
        )

        # 4. 정렬 결과 저장
        update_project(
            request.job_id,
            {
                "subtitles": result,
            },
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
        logger.exception("자막 정렬 실패")

        raise HTTPException(
            status_code=500,
            detail="자막 정렬 중 오류가 발생했습니다.",
        )