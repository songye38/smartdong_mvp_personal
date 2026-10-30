from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.crawler import scrape_naver_blog
from app.services.script_generator import generate_script
from app.services.image_allocator import allocate_images

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["script"])


class ScriptRequest(BaseModel):
    url: str


@router.post("/script")
def create_script(request: ScriptRequest):
    try:
        blog_data = scrape_naver_blog(request.url)

        if not blog_data["sections"]:
            raise HTTPException(
                status_code=422,
                detail="블로그에서 분석할 내용을 찾지 못했습니다.",
            )

        script = generate_script(blog_data)
        script["scenes"] = allocate_images(
        script["scenes"],
        blog_data["images"],
        )

        return {
            "success": True,
            "data": {
                "blog_title": blog_data["title"],
                "script": script,
            },
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        logger.exception("대본 생성 실패")
        raise HTTPException(
            status_code=500,
            detail="대본 생성 중 오류가 발생했습니다.",
        )