def allocate_images(scenes: list, images: list) -> list:
    """
    대본 길이에 비례하여 이미지를 각 장면에 배분한다.
    """

    if not scenes:
        return []

    # 이미지 중복 제거
    unique_images = list(dict.fromkeys(images))

    image_count = len(unique_images)

    # 각 장면의 내레이션 길이
    lengths = [
        len(scene.get("narration", "").strip())
        for scene in scenes
    ]

    total_length = sum(lengths)

    # 대본이 비어 있거나 이미지가 없는 경우
    if total_length == 0 or image_count == 0:
        return [
            {**scene, "images": []}
            for scene in scenes
        ]

    # 글자 수에 따른 이미지 배분 비율
    exact_counts = [
        length / total_length * image_count
        for length in lengths
    ]

    # 우선 정수 부분만 배분
    counts = [
        int(count)
        for count in exact_counts
    ]

    # 남은 이미지는 소수점이 큰 순서대로 배분
    remaining = image_count - sum(counts)

    priorities = sorted(
        range(len(scenes)),
        key=lambda i: exact_counts[i] - counts[i],
        reverse=True,
    )

    for index in priorities[:remaining]:
        counts[index] += 1

    # 이미지 순서대로 배치
    result = []
    image_index = 0

    for scene, count in zip(scenes, counts):
        assigned = unique_images[
            image_index:image_index + count
        ]

        result.append({
            **scene,
            "images": assigned,
        })

        image_index += count

    return result