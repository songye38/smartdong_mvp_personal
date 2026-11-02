import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"


def save_project(job_id: str, data: dict):
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    project_path = job_dir / "project.json"
    temp_path = job_dir / "project.json.tmp"

    data["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    temp_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp_path.replace(project_path)

    return project_path


def load_project(job_id: str):
    project_path = OUTPUT_DIR / job_id / "project.json"

    if not project_path.exists():
        raise FileNotFoundError(
            f"프로젝트를 찾을 수 없습니다: {job_id}"
        )

    return json.loads(
        project_path.read_text(encoding="utf-8")
    )


def update_project(job_id: str, **updates):
    project = load_project(job_id)

    project.update(updates)

    save_project(job_id, project)

    return project