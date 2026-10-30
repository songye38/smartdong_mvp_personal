def create_edit_plan(
    script_scenes: list[dict],
    tts_scenes: list[dict],
) -> dict:
    """
    대본 장면과 TTS 결과를 결합하여 영상 편집 계획 생성.

    - scene_id를 기준으로 두 데이터를 연결
    - TTS 음성 길이를 기준으로 장면 시간 계산
    - 이미지 개수에 따라 표시 시간 균등 배분
    - narration을 자막 원문으로 사용
    """

    if not script_scenes:
        raise ValueError("대본 장면이 없습니다.")

    if not tts_scenes:
        raise ValueError("TTS 장면이 없습니다.")

    # TTS 결과를 scene_id로 검색할 수 있도록 변환
    tts_map = {
        scene["scene_id"]: scene
        for scene in tts_scenes
    }

    result_scenes = []
    current_time = 0.0

    for script_scene in script_scenes:
        scene_id = script_scene["scene_id"]

        # 해당 장면의 TTS 결과 찾기
        tts_scene = tts_map.get(scene_id)

        if not tts_scene:
            raise ValueError(
                f"{scene_id}에 해당하는 TTS 결과가 없습니다."
            )

        narration = script_scene.get("narration", "")
        images = script_scene.get("images", [])

        duration = float(tts_scene["duration"])

        if duration <= 0:
            raise ValueError(
                f"{scene_id}의 음성 길이가 올바르지 않습니다."
            )

        scene_start = current_time
        scene_end = scene_start + duration

        # 이미지별 표시 시간 계산
        shots = []

        if images:
            image_duration = duration / len(images)

            for index, image_url in enumerate(images):
                shot_start = (
                    scene_start + image_duration * index
                )

                # 마지막 이미지는 장면 종료 시점에 맞춤
                if index == len(images) - 1:
                    shot_end = scene_end
                else:
                    shot_end = (
                        scene_start
                        + image_duration * (index + 1)
                    )

                shots.append({
                    "shot_id": f"{scene_id}_shot_{index + 1:03d}",
                    "image_url": image_url,
                    "start_time": round(shot_start, 3),
                    "end_time": round(shot_end, 3),
                    "duration": round(
                        shot_end - shot_start, 3
                    ),
                })

        # 이미지가 없는 경우 검은 배경으로 처리할 수 있도록 표시
        else:
            shots.append({
                "shot_id": f"{scene_id}_shot_001",
                "image_url": None,
                "start_time": round(scene_start, 3),
                "end_time": round(scene_end, 3),
                "duration": round(duration, 3),
            })

        result_scenes.append({
            "scene_id": scene_id,
            "start_time": round(scene_start, 3),
            "end_time": round(scene_end, 3),
            "duration": round(duration, 3),

            # 음성 파일
            "audio_url": tts_scene["audio_url"],

            # 나레이션 원문을 자막으로 사용
            "narration": narration,
            "subtitle_text": narration,

            # 이미지 편집 계획
            "shots": shots,
        })

        current_time = scene_end

    total_duration = round(current_time, 3)

    return {
        "video": {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "total_duration": total_duration,
            "duration_valid": 30 <= total_duration <= 60,
        },
        "scenes": result_scenes,
    }