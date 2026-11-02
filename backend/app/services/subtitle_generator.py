import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=120.0)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"


def split_into_subtitles(words: list[dict], max_chars: int = 18) -> list[dict]:
    """
    단어별 타임스탬프를 화면에 표시할 자막 단위로 묶는다.
    """
    subtitles = []
    current_words = []

    for word in words:
        current_words.append(word)

        text = " ".join(w["word"].strip() for w in current_words)

        if len(text) >= max_chars or re.search(r"[.!?]$", word["word"].strip()):
            subtitles.append({
                "text": text,
                "start_time": round(current_words[0]["start"], 3),
                "end_time": round(current_words[-1]["end"], 3),
            })
            current_words = []

    if current_words:
        subtitles.append({
            "text": " ".join(w["word"].strip() for w in current_words),
            "start_time": round(current_words[0]["start"], 3),
            "end_time": round(current_words[-1]["end"], 3),
        })

    return subtitles


def generate_subtitles(
    job_id: str,
    scenes: list[dict],
) -> dict:
    """
    저장된 MP3 파일에서 단어별 타임스탬프를 추출하고
    장면별 자막 데이터를 생성한다.
    """

    job_dir = OUTPUT_DIR / job_id

    if not job_dir.is_dir():
        raise ValueError("해당 TTS 작업 폴더가 없습니다.")

    result_scenes = []
    current_time = 0.0

    for scene in scenes:
        scene_id = scene["scene_id"]
        duration = float(scene["duration"])

        # TTS 생성 시 저장한 MP3 파일
        audio_path = job_dir / f"{scene_id}.mp3"

        if not audio_path.is_file():
            raise ValueError(f"{scene_id} 음성 파일을 찾을 수 없습니다.")

        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word"],
                language="ko",
            )

        words = [
            {
                "word": word.word,
                "start": float(word.start),
                "end": float(word.end),
            }
            for word in transcription.words
        ]

        # 장면 내부의 상대 시간을 기준으로 자막 생성
        subtitles = split_into_subtitles(words)

        # 전체 영상 기준 시간으로 변환
        for subtitle in subtitles:
            subtitle["start_time"] = round(
                subtitle["start_time"] + current_time, 3
            )
            subtitle["end_time"] = round(
                subtitle["end_time"] + current_time, 3
            )

        result_scenes.append({
            "scene_id": scene_id,
            "narration": scene.get("narration", ""),
            "subtitles": subtitles,
        })

        current_time += duration

    return {
        "job_id": job_id,
        "total_duration": round(current_time, 3),
        "scenes": result_scenes,
    }