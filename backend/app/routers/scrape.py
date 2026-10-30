#React에서 전달한 URL을 받아 응답하는 API



import requests

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.crawler import scrape_naver_blog


router = APIRouter(
    prefix="/api",
    tags=["Scraping"],
)


class ScrapeRequest(BaseModel):
    url: str


@router.post("/scrape")
def scrape_blog(request: ScrapeRequest):
    try:
        result = scrape_naver_blog(request.url)

        return {
            "success": True,
            "data": result,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="네이버 블로그 페이지를 가져오지 못했습니다.",
        )