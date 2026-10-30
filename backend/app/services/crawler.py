#실제 네이버 블로그에 접근해 데이터를 추출하는 코드

import ipaddress
import re
import socket
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

ALLOWED_HOSTS = {
    "blog.naver.com",
    "m.blog.naver.com",
}


def validate_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("HTTP 또는 HTTPS 주소만 사용할 수 있습니다.")

    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("네이버 블로그 주소만 입력할 수 있습니다.")

    # 서버가 내부 네트워크 주소에 접근하지 않도록 확인
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname, None, type=socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise ValueError("블로그 주소를 확인할 수 없습니다.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError("접근할 수 없는 주소입니다.")


def fetch_html(session: requests.Session, url: str):
    validate_url(url)

    response = session.get(
        url,
        timeout=15,
        allow_redirects=False,
    )

    # 예상하지 못한 리다이렉트는 따라가지 않음
    if response.is_redirect:
        raise ValueError("리다이렉트된 블로그 주소는 지원하지 않습니다.")

    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def scrape_naver_blog(url: str):
    validate_url(url)

    session = requests.Session()
    session.headers.update(HEADERS)

    soup = fetch_html(session, url)

    # 네이버 블로그 PC 페이지의 iframe 처리
    iframe = soup.select_one("iframe#mainFrame")

    if iframe and iframe.get("src"):
        iframe_url = urljoin(url, iframe["src"])
        soup = fetch_html(session, iframe_url)

    # 스마트에디터 ONE / 구형 에디터
    content = (
        soup.select_one(".se-main-container")
        or soup.select_one("#postViewArea")
    )

    if not content:
        raise ValueError(
            "블로그 본문을 찾을 수 없습니다. "
            "비공개 게시글이거나 지원하지 않는 페이지 구조일 수 있습니다."
        )

    # 제목 추출
    title_element = (
        soup.select_one(".se-title-text")
        or soup.select_one(".pcol1 .title")
        or soup.select_one("meta[property='og:title']")
    )

    if title_element:
        title = (
            title_element.get("content", "")
            if title_element.name == "meta"
            else title_element.get_text(" ", strip=True)
        )
    else:
        title = "제목 없음"

    blocks = []
    images = []

    # 본문 요소를 문서 순서대로 탐색
    for element in content.select(
        ".se-text-paragraph, .se-image-resource, #postViewArea p, #postViewArea img"
    ):
        if element.name == "img":
            image_url = (
                element.get("data-lazy-src")
                or element.get("data-src")
                or element.get("src")
            )

            if image_url:
                image_url = urljoin(url, image_url)

                images.append(image_url)

                blocks.append({
                    "type": "image",
                    "url": image_url,
                })

        else:
            text = element.get_text(" ", strip=True)

            if text:
                blocks.append({
                    "type": "text",
                    "content": text,
                })

    # 스마트에디터의 이미지 요소가 중첩되어 있는 경우
    # 추출 누락이나 중복이 발생할 수 있으므로
    # 실제 게시글을 이용한 추가 검증이 필요함

    full_text = content.get_text("\n", strip=True)

    return {
        "title": title,
        "url": url,
        "content": full_text,
        "images": list(dict.fromkeys(images)),
        "blocks": blocks,
        "image_count": len(set(images)),
    }