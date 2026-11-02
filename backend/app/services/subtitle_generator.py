import os
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    timeout=120.0,
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"


def normalize_for_alignment(text: str) -> str:
    """
    자막과 Whisper 결과를 비교하기 위한 정규화.

    공백과 문장부호는 제거하지만
    한글, 영문, 숫자는 유지한다.
    """
    text = unicodedata.normalize("NFKC", text)
    return "".join(
        char.lower()
        for char in text
        if char.isalnum()
    )


def get_whisper_words(audio_path: Path) -> list[dict]:
    """Whisper에서 단어별 타임스탬프를 가져온다."""

    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word"],
            language="ko",
        )

    return [
        {
            "word": word.word,
            "start": float(word.start),
            "end": float(word.end),
        }
        for word in transcription.words
    ]


def build_character_timeline(words: list[dict]) -> tuple[str, list[dict]]:
    """
    Whisper 단어들을 하나의 문자열로 합치고
    각 글자가 어느 시간에 해당하는지 기록한다.

    단어 내부의 시간은 균등하게 추정한다.
    """

    full_text = ""
    timeline = []

    for word in words:
        normalized = normalize_for_alignment(word["word"])

        if not normalized:
            continue

        start = float(word["start"])
        end = float(word["end"])

        char_duration = (end - start) / len(normalized)

        for index, char in enumerate(normalized):
            full_text += char

            timeline.append({
                "start": start + char_duration * index,
                "end": start + char_duration * (index + 1),
            })

    return full_text, timeline


def align_caption_boundaries(
    captions: list[dict],
    words: list[dict],
    duration: float,
) -> list[dict]:
    """
    확정된 자막의 글자 위치를 Whisper의
    글자 타임라인에 대응시킨다.

    매칭되지 않는 구간은 인접한 매칭 결과를
    기준으로 시간을 추정한다.
    """

    if not captions:
        return []

    caption_texts = [
        normalize_for_alignment(caption["text"])
        for caption in captions
    ]

    reference_text = "".join(caption_texts)

    whisper_text, timeline = build_character_timeline(words)

    # Whisper 결과가 없으면 글자 수 비례로 배분
    if not whisper_text or not timeline:
        total_chars = sum(len(text) for text in caption_texts)

        if total_chars == 0:
            raise ValueError("정렬할 자막 텍스트가 없습니다.")

        result = []
        elapsed = 0.0

        for index, caption in enumerate(captions):
            if index == len(captions) - 1:
                end = duration
            else:
                end = elapsed + (
                    duration * len(caption_texts[index]) / total_chars
                )

            result.append({
                "text": caption["text"],
                "style": caption["style"],
                "start_time": round(elapsed, 3),
                "end_time": round(end, 3),
            })

            elapsed = end

        return result

    matcher = SequenceMatcher(
        None,
        reference_text,
        whisper_text,
        autojunk=False,
    )

    # 확정 자막의 각 글자를 Whisper 글자 인덱스에 연결
    character_mapping = {}

    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            character_mapping[block.a + offset] = block.b + offset

    # 자막 경계의 reference_text 인덱스
    boundaries = [0]
    position = 0

    for text in caption_texts:
        position += len(text)
        boundaries.append(position)

    # 각 경계에 대응하는 시간 계산
    boundary_times = [0.0]

    for boundary in boundaries[1:-1]:
        left_index = boundary - 1
        right_index = boundary

        left_time = None
        right_time = None

        # 경계 왼쪽에서 가장 가까운 매칭 문자 탐색
        for index in range(left_index, -1, -1):
            if index in character_mapping:
                whisper_index = character_mapping[index]
                left_time = timeline[whisper_index]["end"]
                break

        # 경계 오른쪽에서 가장 가까운 매칭 문자 탐색
        for index in range(right_index, len(reference_text)):
            if index in character_mapping:
                whisper_index = character_mapping[index]
                right_time = timeline[whisper_index]["start"]
                break

        if left_time is not None and right_time is not None:
            boundary_time = (left_time + right_time) / 2

        elif left_time is not None:
            boundary_time = left_time

        elif right_time is not None:
            boundary_time = right_time

        else:
            boundary_time = duration * boundary / len(reference_text)

        boundary_times.append(boundary_time)

    boundary_times.append(duration)

    # 시간 역전 방지
    for index in range(1, len(boundary_times)):
        boundary_times[index] = max(
            boundary_times[index],
            boundary_times[index - 1],
        )
        boundary_times[index] = min(
            boundary_times[index],
            duration,
        )

    result = []

    for index, caption in enumerate(captions):
        result.append({
            "text": caption["text"],
            "style": caption["style"],
            "start_time": round(boundary_times[index], 3),
            "end_time": round(boundary_times[index + 1], 3),
        })

    return result


def align_subtitles(
    job_id: str,
    scenes: list[dict],
    styled_subtitles: dict,
) -> dict:
    """
    확정된 자막을 TTS 음성에 정렬한다.

    자막의 텍스트와 스타일은 변경하지 않는다.
    """

    job_dir = OUTPUT_DIR / job_id

    if not job_dir.is_dir():
        raise ValueError("해당 TTS 작업 폴더가 없습니다.")

    styled_by_id = {
        scene["scene_id"]: scene
        for scene in styled_subtitles["scenes"]
    }

    result_scenes = []
    current_time = 0.0

    for scene in scenes:
        scene_id = scene["scene_id"]
        duration = float(scene["duration"])

        styled_scene = styled_by_id.get(scene_id)

        if styled_scene is None:
            raise ValueError(
                f"{scene_id}에 해당하는 자막이 없습니다."
            )

        audio_path = job_dir / f"{scene_id}.mp3"

        if not audio_path.is_file():
            raise ValueError(
                f"{scene_id} 음성 파일을 찾을 수 없습니다."
            )

        words = get_whisper_words(audio_path)

        aligned = align_caption_boundaries(
            captions=styled_scene["captions"],
            words=words,
            duration=duration,
        )

        # 장면 기준 시간을 전체 영상 기준으로 변환
        for subtitle in aligned:
            subtitle["start_time"] = round(
                subtitle["start_time"] + current_time,
                3,
            )
            subtitle["end_time"] = round(
                subtitle["end_time"] + current_time,
                3,
            )

        result_scenes.append({
            "scene_id": scene_id,
            "narration": styled_scene["narration"],
            "subtitles": aligned,
        })

        current_time += duration

    return {
        "job_id": job_id,
        "total_duration": round(current_time, 3),
        "scenes": result_scenes,
    }