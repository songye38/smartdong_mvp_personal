import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from mutagen.mp3 import MP3
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    timeout=120.0,
)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"


def generate_tts(scenes: list[dict]) -> dict:
    """
    쇼츠 대본의 각 장면을 MP3로 변환한다.
    장면별 음성 길이와 전체 길이를 반환한다.
    """

    if not scenes:
        raise ValueError("음성을 생성할 장면이 없습니다.")

    job_id = uuid.uuid4().hex
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    result_scenes = []
    total_duration = 0.0

    for index, scene in enumerate(scenes, start=1):
        narration = scene.get("narration", "").strip()

        if not narration:
            raise ValueError(
                f"{index}번째 장면에 나레이션이 없습니다."
            )

        scene_id = f"scene_{index:03d}"
        filename = f"{scene_id}.mp3"
        output_path = job_dir / filename

        # OpenAI TTS 생성
        with client.audio.speech.with_streaming_response.create(
            model=os.getenv(
                "OPENAI_TTS_MODEL",
                "gpt-4o-mini-tts",
            ),
            voice=os.getenv(
                "OPENAI_TTS_VOICE",
                "coral",
            ),
            input=narration,
            speed=1.2,
            instructions=(
                "한국어 교육 콘텐츠의 나레이션입니다. "
                "명확하고 자연스러운 발음으로 읽어주세요. "
                "지나치게 빠르지 않게, 친근하고 "
                "신뢰감 있는 말투로 읽어주세요."
            ),
            response_format="mp3",
        ) as response:
            response.stream_to_file(output_path)

        # 실제 MP3 재생 시간 측정
        audio = MP3(str(output_path))
        duration = round(audio.info.length, 2)

        total_duration += duration

        result_scenes.append({
            "scene_id": scene_id,
            "narration": narration,
            "audio_url": f"/outputs/{job_id}/{filename}",
            "duration": duration,
            "images": scene.get("images", []),
        })

    total_duration = round(total_duration, 2)

    return {
        "job_id": job_id,
        "total_duration": total_duration,
        "duration_valid": 30 <= total_duration <= 60,
        "scenes": result_scenes,
    }