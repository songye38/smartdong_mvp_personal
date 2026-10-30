import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.edit_planner import create_edit_plan

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["edit-plan"],
)


class ScriptScene(BaseModel):
    scene_id: str
    narration: str
    images: list[str] = Field(default_factory=list)


class TTSScene(BaseModel):
    scene_id: str
    audio_url: str
    duration: float


class EditPlanRequest(BaseModel):
    script_scenes: list[ScriptScene]
    tts_scenes: list[TTSScene]


@router.post("/edit-plan")
def generate_edit_plan(request: EditPlanRequest):
    try:
        # Pydantic 모델을 dict로 변환
        script_scenes = [
            scene.dict()
            for scene in request.script_scenes
        ]

        tts_scenes = [
            scene.dict()
            for scene in request.tts_scenes
        ]

        result = create_edit_plan(
            script_scenes=script_scenes,
            tts_scenes=tts_scenes,
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
        logger.exception("영상 편집 계획 생성 실패")

        raise HTTPException(
            status_code=500,
            detail="영상 편집 계획 생성 중 오류가 발생했습니다.",
        )