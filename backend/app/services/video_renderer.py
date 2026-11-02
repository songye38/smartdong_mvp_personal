import re
import subprocess
import tempfile
import shutil
import urllib.request

from pathlib import Path


from app.services.subtitle_styles import SUBTITLE_STYLES


# ============================================================
# 기본 설정
# ============================================================

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

FFMPEG_PATH = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"


# ============================================================
# FFmpeg 실행
# ============================================================

def run_ffmpeg(command, cwd=None):
    """
    FFmpeg 명령어를 실행한다.

    기존 ffmpeg-full 경로를 사용해
    ASS 자막 렌더링을 지원한다.
    """

    command = [FFMPEG_PATH, *command[1:]]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg 실행 실패:\n{result.stderr[-3000:]}"
        )


# ============================================================
# 이미지 다운로드
# ============================================================

def download_image(url, destination):
    """
    이미지 URL에서 파일을 다운로드한다.

    - 이미지 Content-Type 확인
    - 최대 15MB 제한
    - 다운로드 실패 시 False 반환
    """

    if not url:
        return False

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if not content_type.startswith("image/"):
                return False

            data = response.read(
                15 * 1024 * 1024 + 1
            )

            if len(data) > 15 * 1024 * 1024:
                return False

        destination.write_bytes(data)

        return True

    except Exception as error:
        print(f"[이미지 다운로드 실패] {error}")
        return False


# ============================================================
# ASS 자막 시간 변환
# ============================================================

def ass_timestamp(seconds):
    """
    초 단위를 ASS 시간 형식으로 변환한다.

    예:
    65.34 → 0:01:05.34
    """

    centiseconds = round(
        float(seconds) * 100
    )

    hours, remainder = divmod(
        centiseconds,
        360000,
    )

    minutes, remainder = divmod(
        remainder,
        6000,
    )

    secs, centis = divmod(
        remainder,
        100,
    )

    return (
        f"{hours}:"
        f"{minutes:02}:"
        f"{secs:02}."
        f"{centis:02}"
    )


# ============================================================
# ASS 색상 변환
# ============================================================

def ass_color(hex_color: str, opacity: float = 1.0) -> str:
    """
    HEX 색상을 ASS 색상으로 변환한다.

    opacity:
        1.0 = 완전 불투명
        0.0 = 완전 투명
    """

    color = hex_color.lstrip("#")

    if len(color) != 6:
        raise ValueError(
            f"올바르지 않은 HEX 색상: {hex_color}"
        )

    if not 0.0 <= opacity <= 1.0:
        raise ValueError(
            f"불투명도는 0~1 사이여야 합니다: {opacity}"
        )

    red = color[0:2]
    green = color[2:4]
    blue = color[4:6]

    alpha = round((1 - opacity) * 255)

    return f"&H{alpha:02X}{blue}{green}{red}"


# ============================================================
# ASS 텍스트 이스케이프
# ============================================================

def escape_ass_text(text):
    """
    자막 텍스트의 ASS 제어문자를 처리한다.

    AI가 생성한 텍스트가
    스타일 명령으로 해석되는 것을 방지한다.
    """

    text = text.replace("\\", "＼")

    text = text.replace(
        "{",
        "｛",
    ).replace(
        "}",
        "｝",
    )

    text = text.replace(
        "\n",
        " ",
    )

    text = text.replace(
        "\r",
        " ",
    )

    return text


# ============================================================
# ASS 자막 파일 생성
# ============================================================

def create_ass(subtitle_scenes, output_path, hook="", total_duration=None):
    """
    자막 문구, 시간, 스타일을 이용해
    ASS 자막 파일을 생성한다.

    지원 스타일:
    - default
    - highlight
    - impact

    모든 스타일은 동일한 크기와 위치를 사용한다.
    """

    lines = [
        "[Script Info]",
        "Title: Auto Generated Shorts Subtitles",
        "ScriptType: v4.00+",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, "
            "PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, "
            "MarginV, Encoding"
        ),
    ]

    # --------------------------------------------------------
    # 스타일 등록
    # --------------------------------------------------------


    ASS_STYLE_NAMES = {
        "default": "CaptionDefault",
        "highlight": "CaptionHighlight",
        "impact": "CaptionImpact",
    }   

    for style_name, config in SUBTITLE_STYLES.items():

        ass_style_name = ASS_STYLE_NAMES[style_name]

        # 1. 폰트 설정
        font = config["font"]
        font_size = config["font_size"]

        # 2. 글자 색상
        primary_color = ass_color(
            config["color"]
        )

        # 3. 외곽선 색상
        outline_color = ass_color(
            config["outline_color"]
        )

        # 4. 배경 색상 및 투명도
        background_color = ass_color(
            config.get("background_color", "#000000"),
            config.get("background_opacity", 0.65)
        )

        # 5. 배경 박스 여백
        background_padding = config.get(
            "background_padding", 15
        )

        # 6. 자막 위치
        margin_v = config.get("margin_v", 620)

        lines.append(
            "Style: "
            f"{ass_style_name},"
            f"{font},"
            f"{font_size},"
            f"{primary_color},"
            "&H00000000,"          # SecondaryColour
            f"{outline_color},"    # OutlineColour
            f"{background_color}," # BackColour
            "-1,"                  # Bold
            "0,"                   # Italic
            "0,"                   # Underline
            "0,"                   # StrikeOut
            "100,"                 # ScaleX
            "100,"                 # ScaleY
            "0,"                   # Spacing
            "0,"                   # Angle
            "3,"                   # BorderStyle: 배경 박스
            f"{background_padding},"  # Outline: 박스 여백
            "0,"                   # Shadow
            "2,"                   # Alignment: 하단 중앙
            "60,"                  # MarginL
            "60,"                  # MarginR
            f"{margin_v},"         # MarginV
            "1"                    # Encoding
        )
    
    
    
    # 상단 고정 훅 전용 스타일 (기존 하단 자막 스타일은 변경하지 않음)
    lines.append(
        "Style: "
        "HookTop,"
        "Pretendard Black,"
        "120,"
        "&H00FFFFFF,"
        "&H00000000,"
        "&H00000000,"
        "&H80000000,"
        "-1,0,0,0,100,100,0,0,1,4,1,"
        "8,80,80,250,1"
    )

    # --------------------------------------------------------
    # 자막 이벤트 설정
    # --------------------------------------------------------

    lines.extend([
        "",
        "[Events]",
        (
            "Format: Layer, Start, End, Style, "
            "Name, MarginL, MarginR, "
            "MarginV, Effect, Text"
        ),
    ])

    subtitle_count = 0

    # --------------------------------------------------------
    # 자막 이벤트 생성
    # --------------------------------------------------------

    for scene in subtitle_scenes:

        for subtitle in scene.get(
            "subtitles",
            [],
        ):

            start = float(
                subtitle["start_time"]
            )

            end = float(
                subtitle["end_time"]
            )

            text = subtitle["text"].strip()

            style = subtitle.get(
                "style",
                "default",
            )

            # 비어 있거나 시간이 잘못된 자막 제외
            if not text or end <= start:
                continue

            # 정의되지 않은 스타일은 default
            if style not in SUBTITLE_STYLES:
                style = "default"

            ass_style_name = ASS_STYLE_NAMES[style]

            safe_text = escape_ass_text(
                text
            )

            lines.append(
                "Dialogue: "
                f"0,"
                f"{ass_timestamp(start)},"
                f"{ass_timestamp(end)},"
                f"{ass_style_name},"
                ","
                "0,0,0,,"
                f"{safe_text}"
            )

            subtitle_count += 1

    # 상단 고정 훅: 한 개의 ASS 이벤트로 영상 전체에 표시
    if hook and str(hook).strip():
        if total_duration is None:
            total_duration = max(
                (
                    float(item.get("end_time", 0))
                    for scene in subtitle_scenes
                    for item in scene.get("subtitles", [])
                ),
                default=0.0,
            )

        hook_lines = [
            part.strip()
            for part in str(hook).replace("\r\n", "\n").split("\n")
            if part.strip()
        ]
        # 줄바꿈이 없으면 한 줄로 표시하며, 세 줄 이상이면 두 줄로 합침
        if len(hook_lines) > 2:
            hook_lines = [hook_lines[0], " ".join(hook_lines[1:])]
        safe_hook = r"\N".join(escape_ass_text(part) for part in hook_lines)

        if safe_hook and float(total_duration) > 0:
            lines.append(
                "Dialogue: "
                f"1,{ass_timestamp(0)},{ass_timestamp(total_duration)},"
                f"HookTop,,0,0,0,,{safe_hook}"
            )

    output_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("[ASS 파일 경로]", output_path)
    print("[자막 스타일 설정]")
    print("\n".join(
        line for line in lines
        if line.startswith("Style:")
    ))

    print(
        f"[ASS 생성 완료] "
        f"{subtitle_count}개 자막"
    )


# ============================================================
# 이미지 클립 생성
# ============================================================

def create_image_clip(
    image_path,
    duration,
    output_path,
):
    """
    이미지 한 장을 지정된 길이의
    영상 클립으로 변환한다.

    이미지가 없으면 검은색 배경을 사용한다.
    """

    frames = max(
        1,
        round(duration * FPS),
    )

    if image_path:

        input_args = [
            "-loop", "1",
            "-i", str(image_path),
        ]

    else:

        input_args = [
            "-f", "lavfi",
            "-i",
            (
                f"color=c=black:"
                f"s={WIDTH}x{HEIGHT}:"
                f"r={FPS}"
            ),
        ]

    IMAGE_WIDTH = 1080
    IMAGE_HEIGHT = 780
    IMAGE_Y = 580

    video_filter = (
        f"scale={IMAGE_WIDTH}:{IMAGE_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={IMAGE_WIDTH}:{IMAGE_HEIGHT},"
        f"pad={WIDTH}:{HEIGHT}:0:{IMAGE_Y}:black,"
        "setsar=1,"
        "format=yuv420p"
    )

    command = [
        "ffmpeg", "-y",
        *input_args,
        "-vf", video_filter,
        "-frames:v", str(frames),
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    run_ffmpeg(command)


# ============================================================
# FFmpeg concat 목록 생성
# ============================================================

def write_concat_file(
    paths,
    destination,
):
    """
    FFmpeg concat demuxer용
    파일 목록을 생성한다.
    """

    lines = []

    for path in paths:

        escaped = str(path).replace(
            "'",
            "'\\''",
        )

        lines.append(
            f"file '{escaped}'"
        )

    destination.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


# ============================================================
# 최종 영상 렌더링
# ============================================================

def render_video(
    job_id,
    edit_plan,
    subtitle_scenes,
    hook,
):
    """
    이미지 + TTS + ASS 자막을 합쳐
    최종 쇼츠 영상을 생성한다.

    subtitle_scenes에는
    align_subtitles() 결과의 scenes 배열을 전달한다.
    """

    # --------------------------------------------------------
    # 작업 ID 검증
    # --------------------------------------------------------

    if not re.fullmatch(
        r"[a-f0-9]{32}",
        job_id,
    ):
        raise ValueError(
            "올바르지 않은 job_id입니다."
        )

    job_dir = OUTPUT_DIR / job_id

    if not job_dir.is_dir():
        raise ValueError(
            "TTS 작업 폴더를 찾을 수 없습니다."
        )

    scenes = edit_plan.get(
        "scenes",
        [],
    )

    if not scenes:
        raise ValueError(
            "영상 편집 계획이 없습니다."
        )

    output_path = (
        job_dir / "final_test.mp4"
    )

    # --------------------------------------------------------
    # 임시 작업 폴더 생성
    # --------------------------------------------------------

    with tempfile.TemporaryDirectory(
        prefix="render_",
        dir=job_dir,
    ) as temp_dir:

        temp = Path(temp_dir)

        clips = []
        audio_files = []

        # ====================================================
        # 1. 이미지 클립 생성
        # ====================================================

        for scene_index, scene in enumerate(scenes):

            scene_id = scene["scene_id"]

            audio_path = (
                job_dir / f"{scene_id}.mp3"
            )

            if not audio_path.is_file():
                raise ValueError(
                    f"{scene_id} MP3 파일이 없습니다."
                )

            audio_files.append(
                audio_path
            )

            for shot_index, shot in enumerate(
                scene["shots"]
            ):

                image_url = shot.get(
                    "image_url"
                )

                image_path = None

                # 이미지 다운로드
                if image_url:

                    downloaded_path = (
                        temp
                        / f"image_{scene_index}_{shot_index}"
                    )

                    if download_image(
                        image_url,
                        downloaded_path,
                    ):
                        image_path = (
                            downloaded_path
                        )

                clip_path = (
                    temp
                    / f"clip_{scene_index}_{shot_index}.mp4"
                )

                create_image_clip(
                    image_path=image_path,
                    duration=float(
                        shot["duration"]
                    ),
                    output_path=clip_path,
                )

                clips.append(
                    clip_path
                )

        if not clips:
            raise ValueError(
                "생성할 이미지 클립이 없습니다."
            )

        # ====================================================
        # 2. 이미지 클립 연결
        # ====================================================

        video_list = (
            temp / "videos.txt"
        )

        write_concat_file(
            clips,
            video_list,
        )

        combined_video = (
            temp / "combined.mp4"
        )

        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(video_list),
            "-c", "copy",
            str(combined_video),
        ])

        # ====================================================
        # 3. MP3 연결
        # ====================================================

        audio_list = (
            temp / "audios.txt"
        )

        write_concat_file(
            audio_files,
            audio_list,
        )

        combined_audio = (
            temp / "combined.mp3"
        )

        run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(audio_list),
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(combined_audio),
        ])

        if not combined_audio.is_file():
            raise RuntimeError(
                "combined.mp3 생성에 실패했습니다."
            )

        # ====================================================
        # 4. ASS 자막 생성
        # ====================================================

        subtitle_path = (
            temp / "subtitles.ass"
        )

        create_ass(
            subtitle_scenes,
            subtitle_path,
            hook=hook,
            total_duration=edit_plan.get("video", {}).get("total_duration"),
        )

        # 디버깅용 ASS 파일 별도 저장

        debug_subtitle_path = job_dir / "debug_subtitles.ass"

        shutil.copy2(
            subtitle_path,
            debug_subtitle_path,
        )

        print(f"[디버그 ASS 저장 완료] {debug_subtitle_path}")

        # ====================================================
        # 5. ASS 자막 필터
        # ====================================================

        subtitle_filter = (
            "ass=filename=subtitles.ass"
        )

        # ====================================================
        # 6. 최종 영상 렌더링
        # ====================================================

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

    # ========================================================
    # 결과 반환
    # ========================================================

    return {
        "job_id": job_id,
        "video_url": f"/outputs/{job_id}/final_test.mp4",
        "filename": "final_test.mp4",
    }