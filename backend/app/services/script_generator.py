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
11. 첫 번째 장면의 narration은 시청자의 관심을 끄는 문장으로 시작하세요.

상단 고정 훅 작성 원칙:
1. 영상 전체에 고정 표시할 hook을 별도로 생성하세요.
2. hook은 나레이션과 구분되는 화면용 문구입니다.
3. 영상의 핵심 내용을 바탕으로 호기심을 유발하세요.
4. 구체적인 사건, 문제, 반전, 궁금증을 활용하세요.
5. 과장하거나 원문에 없는 사실을 만들지 마세요.
6. hook은 최대 2줄로 작성하세요.
7. 각 줄은 공백 포함 10자를 절대 초과하지 마세요.
8. 전체 길이는 줄바꿈을 제외하고 공백 포함 20자 이내로 작성하세요.
9. 가능하면 전체 12~18자로 작성하세요.
10. 설명형 문장보다 짧고 직관적인 헤드라인을 우선하세요.
11. 불필요한 조사, 수식어, 반복 표현을 제거하세요.
12. 줄바꿈이 필요하면 \\n을 사용하세요.
13. 영상 제목을 그대로 반복하지 마세요.
14. hook은 TTS로 읽지 않습니다.

반드시 다음 JSON 형식으로 반환하세요.

{
  "title": "쇼츠 제목",
  "hook": "영상 상단에 고정할 훅 문구",
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
            "extra_images": section.get("extra_images", []),
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

    # 필수 필드 검증
    if not isinstance(result, dict):
        raise ValueError("AI 대본 결과가 JSON 객체가 아닙니다.")

    if not isinstance(result.get("title"), str):
        raise ValueError("쇼츠 제목이 없습니다.")

    if not isinstance(result.get("hook"), str):
        raise ValueError("상단 고정 훅이 생성되지 않았습니다.")

    if not result["hook"].strip():
        raise ValueError("상단 고정 훅이 비어 있습니다.")

    if not isinstance(result.get("scenes"), list):
        raise ValueError("쇼츠 장면 데이터가 없습니다.")

    result["hook"] = result["hook"].strip()

    return result