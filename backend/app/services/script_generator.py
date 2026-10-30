import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """
당신은 온라인 교육회사의 유튜브 쇼츠 콘텐츠 기획자입니다.

목표:
블로그 글을 바탕으로 30~60초 분량의 한국어 쇼츠 대본을 작성합니다.
우선 40~50초 분량을 목표로 합니다.

작성 원칙:
1. 원문을 단순히 요약하지 말고 시청자가 이해하기 쉽게 재구성하세요.
2. 하나의 핵심 주제에 집중하세요.
3. 첫 문장은 시청자의 관심을 끌어야 합니다.
4. 원문에 없는 구체적인 사실이나 수치를 지어내지 마세요.
5. 자연스러운 구어체로 작성하세요.
6. 불필요한 광고 문구를 넣지 마세요.
7. 전체 대본은 자연스럽게 연결되어야 합니다.
8. 대본을 3~5개의 장면으로 구분하세요.
9. 각 장면의 narration은 실제 TTS에서 읽을 문장입니다.
10. 별도의 caption은 생성하지 마세요.
11. hook은 첫 번째 장면의 narration에 포함하세요.

반드시 다음 JSON 형식으로 반환하세요.

{
  "title": "쇼츠 제목",
  "scenes": [
    {
      "scene_id": "scene_001",
      "narration": "실제 나레이션 대본"
    }
  ]
}
"""


def generate_script(blog_data: dict) -> dict:
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        timeout=60.0,
    )

    sections = [
        {
            "id": section["id"],
            "text": section["text"],
            "image_url": section["image_url"],
            "extra_images": section["extra_images"],
        }
        for section in blog_data["sections"]
    ]

    payload = {
        "title": blog_data["title"],
        "sections": sections,
    }

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=SYSTEM_PROMPT,
        input=(
            "다음 블로그 데이터를 분석하고, "
            "쇼츠 대본을 반드시 JSON 형식으로 생성하세요.\n\n"
            + json.dumps(payload, ensure_ascii=False)
        ),
        text={
            "format": {
                "type": "json_object"
            }
        },
        store=False,
    )

    result = json.loads(response.output_text)

    # AI가 반환한 섹션 ID가 실제로 존재하는지 확인
    result = json.loads(response.output_text)

    return result