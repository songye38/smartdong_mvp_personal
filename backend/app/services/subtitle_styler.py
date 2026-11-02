from __future__ import annotations

"""자막 분할은 결정적 규칙으로, 강조 스타일만 AI로 선택한다."""
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=120.0)

VALID_STYLES = {'default', 'highlight', 'impact'}
SHORT_SENTENCE_CHARS = 25
MAX_CAPTION_CHARS = 55  # 안전장치: 지나치게 긴 문장은 추가 분할


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip())


def split_sentences(text: str) -> list[str]:
    """마침표/물음표/느낌표 뒤에서 문장을 나눈다. 문장부호는 보존한다."""
    text = normalize_text(text)
    if not text:
        return []
    return [part.strip() for part in re.split(r'(?<=[.,!?])\s+', text) if part.strip()]


def split_near_middle(text: str) -> tuple[str, str] | None:
    """어절 경계 중 글자 수 균형이 가장 좋은 지점을 선택한다."""
    words = text.split(' ')
    if len(words) < 2:
        return None
    candidates = []
    for i in range(1, len(words)):
        left = ' '.join(words[:i])
        right = ' '.join(words[i:])
        candidates.append((abs(len(left) - len(right)), i, left, right))
    _, _, left, right = min(candidates)
    return left, right


def split_sentence(sentence: str) -> list[str]:
    """짧은 문장은 유지, 긴 문장은 약 절반씩. 매우 긴 문장에는 상한 적용."""
    if len(sentence) <= SHORT_SENTENCE_CHARS:
        return [sentence]
    halves = split_near_middle(sentence)
    if halves is None:
        return [sentence]
    result = []
    for half in halves:
        if len(half) > MAX_CAPTION_CHARS:
            result.extend(split_sentence(half))
        else:
            result.append(half)
    return result


def make_captions(narration: str) -> list[dict]:
    captions = []
    for sentence in split_sentences(narration):
        for chunk in split_sentence(sentence):
            captions.append({'text': chunk, 'style': 'default'})
    return captions


def validate_captions(narration: str, captions: list[dict]) -> bool:
    if not captions or any(
        not isinstance(c, dict)
        or not isinstance(c.get('text'), str)
        or not c['text'].strip()
        or c.get('style') not in VALID_STYLES
        for c in captions
    ):
        return False
    # 분할 과정에서 공백만 변할 수 있으므로 공백만 무시하여 원문 일치 검증
    compact = lambda s: re.sub(r'\s+', '', s)
    return compact(''.join(c['text'] for c in captions)) == compact(narration)


def prepare_subtitles(scenes: list[dict]) -> dict:
    """원문 유지 -> 규칙 기반 분할 -> AI 스타일 지정. TTS에는 반환 narration 사용."""
    input_scenes = []
    for scene in scenes:
        narration = normalize_text(scene['narration'])
        input_scenes.append({
            'scene_id': scene['scene_id'],
            'narration': narration,
            'captions': make_captions(narration),
        })

    prompt = '''너는 숏폼 영상 자막 스타일 편집자다.
입력의 scenes[].captions는 이미 확정된 자막이다.
텍스트, 순서, 개수, scene_id, narration을 절대 수정하지 마라.
각 자막의 스타일만 다음 중 하나로 지정해라:
- default: 일반 설명 (흰색 고딕)
- highlight: 핵심 메시지 (노란색 세리프)
- impact: 경고·반전·강한 문제 제기 (빨간색 세리프)
전체 자막의 약 15~25%를 강조하되 내용상 불필요하면 억지로 강조하지 마라.
반드시 JSON 객체만 반환해라. 출력 형식:
{"scenes": [{"scene_id": "scene_001", "styles": ["default", "highlight"]}]}
styles 배열의 길이는 입력된 해당 장면 captions 개수와 정확히 같아야 한다.'''

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.2,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': json.dumps(input_scenes, ensure_ascii=False)},
            ],
        )
        result = json.loads(response.choices[0].message.content)
        result_by_id = {
            item['scene_id']: item
            for item in result.get('scenes', [])
            if isinstance(item, dict) and isinstance(item.get('scene_id'), str)
        }
    except Exception as exc:
        print(f'[subtitle_styler] AI 스타일 지정 실패, 기본 스타일 사용: {exc}')
        result_by_id = {}

    final_scenes = []
    for scene in input_scenes:
        captions = scene['captions']
        styles = result_by_id.get(scene['scene_id'], {}).get('styles', [])
        if (
            isinstance(styles, list)
            and len(styles) == len(captions)
            and all(style in VALID_STYLES for style in styles)
        ):
            for caption, style in zip(captions, styles):
                caption['style'] = style
            print(f"[{scene['scene_id']}] AI 스타일: {styles}")
        else:
            print(f"[{scene['scene_id']}] AI 스타일 검증 실패, 기본 스타일 유지")

        if not validate_captions(scene['narration'], captions):
            raise ValueError(f"자막 원문 일치 검증 실패: {scene['scene_id']}")
        final_scenes.append(scene)

    return {'scenes': final_scenes}
