import uuid
import logging

from app.services.crawler import scrape_naver_blog
from app.services.script_generator import generate_script
from app.services.image_allocator import allocate_images
from app.services.tts_generator import generate_tts
from app.services.edit_planner import create_edit_plan
from app.services.subtitle_generator import generate_subtitles
from app.services.video_renderer import render_video

from app.services.project_store import (
    save_project,
    update_project,
    load_project,
)

logger = logging.getLogger(__name__)


def generate_video(url: str) -> dict:
    """
    블로그 URL 하나로 쇼츠 MP4를 생성한다.

    1. 크롤링
    2. 대본 생성
    3. 이미지 배분
    4. TTS 생성
    5. 편집 계획 생성
    6. 자막 생성
    7. MP4 렌더링
    """

    job_id = uuid.uuid4().hex
    current_step = "scraping"

    # 최초 프로젝트 생성
    save_project(job_id, {
        "job_id": job_id,
        "source_url": url,
        "status": "processing",
        "current_step": current_step,
        "blog_title": None,
        "script": None,
        "tts": None,
        "edit_plan": None,
        "subtitles": None,
        "video_url": None,
        "error": None,
    })

    try:
        # -----------------------------------
        # 1. 블로그 크롤링
        # -----------------------------------
        blog_data = scrape_naver_blog(url)

        if not blog_data.get("sections"):
            raise ValueError(
                "블로그에서 분석할 내용을 찾지 못했습니다."
            )

        update_project(
            job_id,
            blog_title=blog_data.get("title"),
        )

        # -----------------------------------
        # 2. 대본 생성
        # -----------------------------------
        current_step = "script"
        update_project(
            job_id,
            current_step=current_step,
        )

        script = generate_script(blog_data)

        # -----------------------------------
        # 3. 이미지 배분
        # -----------------------------------
        current_step = "images"
        update_project(
            job_id,
            current_step=current_step,
        )

        script["scenes"] = allocate_images(
            script["scenes"],
            blog_data["images"],
        )

        update_project(
            job_id,
            script=script,
        )

        # -----------------------------------
        # 4. TTS 생성
        # -----------------------------------
        current_step = "tts"
        update_project(
            job_id,
            current_step=current_step,
        )

        tts = generate_tts(
            script["scenes"],
            job_id=job_id,
        )

        update_project(
            job_id,
            tts=tts,
        )

        # -----------------------------------
        # 5. 편집 계획 생성
        # -----------------------------------
        current_step = "edit_plan"
        update_project(
            job_id,
            current_step=current_step,
        )

        edit_plan = create_edit_plan(
            script_scenes=script["scenes"],
            tts_scenes=tts["scenes"],
        )

        update_project(
            job_id,
            edit_plan=edit_plan,
        )

        # -----------------------------------
        # 6. 자막 생성
        # -----------------------------------
        current_step = "subtitles"
        update_project(
            job_id,
            current_step=current_step,
        )

        subtitles = generate_subtitles(
            job_id=job_id,
            scenes=tts["scenes"],
        )

        update_project(
            job_id,
            subtitles=subtitles,
        )

        # -----------------------------------
        # 7. MP4 렌더링
        # -----------------------------------
        current_step = "rendering"
        update_project(
            job_id,
            current_step=current_step,
        )

        video = render_video(
            job_id=job_id,
            edit_plan=edit_plan,
            subtitle_scenes=subtitles["scenes"],
        )

        # -----------------------------------
        # 완료
        # -----------------------------------
        update_project(
            job_id,
            status="completed",
            current_step="completed",
            video_url=video["video_url"],
        )

        return load_project(job_id)

    except Exception as error:
        logger.exception(
            "영상 생성 실패: job_id=%s, step=%s",
            job_id,
            current_step,
        )

        update_project(
            job_id,
            status="failed",
            current_step=current_step,
            error=str(error),
        )

        raise RuntimeError(
            f"영상 생성 실패 "
            f"(job_id={job_id}, 단계={current_step}): {error}"
        ) from error