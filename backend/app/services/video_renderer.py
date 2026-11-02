import re
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"

WIDTH = 1080
HEIGHT = 1920
FPS = 30


def run_ffmpeg(command, cwd=None):
    ffmpeg_path = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"

    command = [ffmpeg_path, *command[1:]]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:])


def download_image(url, destination):
    if not url:
        return False

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if not content_type.startswith("image/"):
                return False

            data = response.read(15 * 1024 * 1024 + 1)

            if len(data) > 15 * 1024 * 1024:
                return False

        destination.write_bytes(data)
        return True

    except Exception:
        return False


def srt_timestamp(seconds):
    milliseconds = round(float(seconds) * 1000)

    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)

    return (
        f"{hours:02}:{minutes:02}:"
        f"{secs:02},{millis:03}"
    )


def create_srt(subtitle_scenes, output_path):
    entries = []
    index = 1

    for scene in subtitle_scenes:
        for subtitle in scene.get("subtitles", []):
            start = float(subtitle["start_time"])
            end = float(subtitle["end_time"])
            content = subtitle["text"].strip()

            if not content or end <= start:
                continue

            entries.append(
                f"{index}\n"
                f"{srt_timestamp(start)} --> "
                f"{srt_timestamp(end)}\n"
                f"{content}\n"
            )

            index += 1

    output_path.write_text(
        "\n".join(entries),
        encoding="utf-8",
    )


def create_image_clip(image_path, duration, output_path):
    frames = max(1, round(duration * FPS))

    if image_path:
        input_args = [
            "-loop", "1",
            "-i", str(image_path),
        ]
    else:
        input_args = [
            "-f", "lavfi",
            "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}",
        ]

    command = [
        "ffmpeg", "-y",
        *input_args,
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,"
            "format=yuv420p"
        ),
        "-frames:v", str(frames),
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    run_ffmpeg(command)


def write_concat_file(paths, destination):
    lines = []

    for path in paths:
        # 임시 경로는 우리가 직접 생성하므로 concat 목록에 사용 가능
        escaped = str(path).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")

    destination.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def render_video(job_id, edit_plan, subtitle_scenes):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise ValueError("올바르지 않은 job_id입니다.")

    job_dir = OUTPUT_DIR / job_id

    if not job_dir.is_dir():
        raise ValueError("TTS 작업 폴더를 찾을 수 없습니다.")

    scenes = edit_plan.get("scenes", [])

    if not scenes:
        raise ValueError("영상 편집 계획이 없습니다.")

    output_path = job_dir / "final.mp4"

    with tempfile.TemporaryDirectory(
        prefix="render_",
        dir=job_dir,
    ) as temp_dir:
        temp = Path(temp_dir)

        clips = []
        audio_files = []

        # 1. 장면별 이미지 클립 생성
        for scene_index, scene in enumerate(scenes):
            scene_id = scene["scene_id"]

            audio_path = job_dir / f"{scene_id}.mp3"

            if not audio_path.is_file():
                raise ValueError(
                    f"{scene_id} MP3 파일이 없습니다."
                )

            audio_files.append(audio_path)

            for shot_index, shot in enumerate(scene["shots"]):
                image_url = shot.get("image_url")
                image_path = None

                if image_url:
                    downloaded_path = (
                        temp / f"image_{scene_index}_{shot_index}"
                    )

                    if download_image(
                        image_url,
                        downloaded_path,
                    ):
                        image_path = downloaded_path

                clip_path = (
                    temp / f"clip_{scene_index}_{shot_index}.mp4"
                )

                create_image_clip(
                    image_path=image_path,
                    duration=float(shot["duration"]),
                    output_path=clip_path,
                )

                clips.append(clip_path)

        # 2. 이미지 클립 연결
        video_list = temp / "videos.txt"
        write_concat_file(clips, video_list)

        combined_video = temp / "combined.mp4"

        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(video_list),
            "-c", "copy",
            str(combined_video),
        ])

        # 3. MP3 연결
        audio_list = temp / "audios.txt"
        write_concat_file(audio_files, audio_list)

        combined_audio = temp / "combined.mp3"

        # 장면별 MP3 파일을 하나로 합치기
        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(audio_list),
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(combined_audio),
        ])

        # 파일 생성 확인
        if not combined_audio.is_file():
            raise RuntimeError(
                "combined.mp3 파일 생성에 실패했습니다."
            )


        # 4. 자막 파일 생성
        subtitle_path = temp / "subtitles.srt"

        create_srt(
            subtitle_scenes,
            subtitle_path,
        )

        # 5. 영상 + 음성 + 자막 합치기
        subtitle_filter = (
            "subtitles=filename=subtitles.srt:"
            "force_style='"
            "FontName=Arial,"
            "FontSize=14,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=2,"
            "Shadow=1,"
            "Alignment=2,"
            "MarginV=120"
            "'"
        )

        # 6. 실제 영상 렌더링
        run_ffmpeg(
            [
                "ffmpeg", "-y",
                "-i", str(combined_video),
                "-i", str(combined_audio),
                "-vf", subtitle_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(output_path),
            ],
            cwd=temp,
        )

    return {
        "job_id": job_id,
        "video_url": f"/outputs/{job_id}/final.mp4",
        "filename": "final.mp4",
    }

