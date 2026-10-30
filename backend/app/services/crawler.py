# 실제 네이버 블로그에 접근해 데이터를 추출하는 코드

import ipaddress
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


# --------------------------------------------------
# 1. URL 검증
# --------------------------------------------------

def validate_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("HTTP 또는 HTTPS 주소만 사용할 수 있습니다.")

    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("네이버 블로그 주소만 입력할 수 있습니다.")

    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        raise ValueError("블로그 주소를 확인할 수 없습니다.")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError("접근할 수 없는 주소입니다.")


# --------------------------------------------------
# 2. HTML 가져오기
# --------------------------------------------------

def fetch_html(session: requests.Session, url: str):
    validate_url(url)

    response = session.get(
        url,
        timeout=15,
        allow_redirects=False,
    )

    if response.is_redirect:
        raise ValueError("리다이렉트된 블로그 주소는 지원하지 않습니다.")

    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


# --------------------------------------------------
# 3. 이미지 URL 추출
# --------------------------------------------------

def get_image_url(element, base_url: str):
    """
    이미지 요소에서 실제 이미지 URL 추출
    """

    image = element if element.name == "img" else element.select_one("img")

    if image is None:
        return None

    image_url = (
        image.get("data-lazy-src")
        or image.get("data-src")
        or image.get("src")
    )

    if not image_url:
        return None

    return urljoin(base_url, image_url)


# --------------------------------------------------
# 4. HTML → blocks 변환
# --------------------------------------------------

def extract_blocks(content, base_url: str):
    """
    블로그 본문의 텍스트와 이미지를
    등장 순서대로 추출
    """

    blocks = []

    # 스마트에디터 ONE
    if content.select_one(".se-component"):

        components = content.select(".se-component")

        for component in components:

            # 텍스트 컴포넌트
            if "se-text" in component.get("class", []):

                paragraphs = component.select(".se-text-paragraph")

                for paragraph in paragraphs:
                    text = paragraph.get_text(" ", strip=True)

                    if text:
                        blocks.append({
                            "type": "text",
                            "content": text,
                        })

            # 이미지 컴포넌트
            elif "se-image" in component.get("class", []):

                images = component.select("img")

                for image in images:
                    image_url = get_image_url(image, base_url)

                    if image_url:
                        blocks.append({
                            "type": "image",
                            "url": image_url,
                        })

    # 구형 에디터
    else:

        for element in content.find_all(["p", "img"]):

            if element.name == "img":

                image_url = get_image_url(element, base_url)

                if image_url:
                    blocks.append({
                        "type": "image",
                        "url": image_url,
                    })

            elif element.name == "p":

                text = element.get_text(" ", strip=True)

                if text:
                    blocks.append({
                        "type": "text",
                        "content": text,
                    })

    return blocks


# --------------------------------------------------
# 5. blocks → sections 변환
# --------------------------------------------------

def create_sections(blocks):
    """
    이미지 1장 + 여분 이미지 + 텍스트를
    하나의 section으로 묶는다.
    """

    sections = []

    current_section = None

    def save_section():
        nonlocal current_section

        if current_section is None:
            return

        # 텍스트 배열을 하나의 문자열로 변환
        current_section["text"] = "\n".join(
            current_section["text"]
        )

        sections.append(current_section)
        current_section = None

    for block in blocks:

        # -------------------------
        # 이미지인 경우
        # -------------------------
        if block["type"] == "image":

            image_url = block["url"]

            # 아직 단락이 없다면 새 단락 생성
            if current_section is None:

                current_section = {
                    "id": "",
                    "image_url": image_url,
                    "extra_images": [],
                    "text": [],
                }

            # 이미지가 없는 도입 단락이라면
            elif current_section["image_url"] is None:

                save_section()

                current_section = {
                    "id": "",
                    "image_url": image_url,
                    "extra_images": [],
                    "text": [],
                }

            # 현재 단락에 텍스트가 없다면 여분 이미지로 추가
            elif not current_section["text"]:

                current_section["extra_images"].append(image_url)

            # 텍스트가 이미 있다면 새 단락 시작
            else:

                save_section()

                current_section = {
                    "id": "",
                    "image_url": image_url,
                    "extra_images": [],
                    "text": [],
                }

        # -------------------------
        # 텍스트인 경우
        # -------------------------
        elif block["type"] == "text":

            text = block["content"]

            # 이미지보다 텍스트가 먼저 등장한 경우
            if current_section is None:

                current_section = {
                    "id": "",
                    "image_url": None,
                    "extra_images": [],
                    "text": [],
                }

            current_section["text"].append(text)

    # 마지막 단락 저장
    save_section()

    # ID 부여
    for index, section in enumerate(sections):
        section["id"] = f"section_{index:03d}"

    return sections


# --------------------------------------------------
# 6. 네이버 블로그 크롤링
# --------------------------------------------------

def scrape_naver_blog(url: str):
    validate_url(url)

    session = requests.Session()
    session.headers.update(HEADERS)

    soup = fetch_html(session, url)

    # 네이버 블로그 PC 페이지 iframe 처리
    iframe = soup.select_one("iframe#mainFrame")

    if iframe and iframe.get("src"):
        iframe_url = urljoin(url, iframe["src"])
        soup = fetch_html(session, iframe_url)

    # 본문 선택
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

    # 원본 순서대로 blocks 생성
    blocks = extract_blocks(content, url)

    # 이미지 기준으로 sections 생성
    sections = create_sections(blocks)

    # 전체 텍스트
    full_text = content.get_text("\n", strip=True)

    # 이미지 목록
    images = [
        block["url"]
        for block in blocks
        if block["type"] == "image"
    ]

    return {
        "title": title,
        "url": url,
        "content": full_text,
        "images": list(dict.fromkeys(images)),
        "blocks": blocks,
        "sections": sections,
        "section_count": len(sections),
        "image_count": len(set(images)),
    }