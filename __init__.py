"""Drama Studio - ComfyUI custom extension (V0.1 scaffold).

This package provides a persistent project/series/episode/shot management layer
inside ComfyUI. It intentionally does not hard-code any specific model workflow
except through pluggable workflow templates in ./workflows/.
"""

from aiohttp import web
from pathlib import Path
import json
import re
import time
import uuid

from server import PromptServer
try:
    import folder_paths
    OUTPUT_DIR = Path(folder_paths.get_output_directory())
except Exception:
    OUTPUT_DIR = Path(__file__).resolve().parent / "output"

DATA_DIR = OUTPUT_DIR / "drama_studio"
PROJECTS_DIR = DATA_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

WEB_DIRECTORY = "./web"


def _safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip())
    return value[:80] or "project"


def _json_path(project_id: str) -> Path:
    return PROJECTS_DIR / _safe_id(project_id) / "project.json"


def _default_project(name: str, synopsis: str = "") -> dict:
    now = int(time.time())
    project_id = f"P_{uuid.uuid4().hex[:8].upper()}"
    return {
        "schema_version": 1,
        "project_id": project_id,
        "name": name.strip() or "Untitled Drama",
        "language": "en",
        "format": "vertical_9_16",
        "genre": "romantic_thriller",
        "episode_count": 10,
        "episode_duration_seconds": 90,
        "synopsis": synopsis.strip(),
        "bible": {
            "story_rules": {
                "dialogue_priority": True,
                "new_dramatic_beat_every_seconds": 20,
                "episode_must_end_with": "cliffhanger",
            },
            "visual_style": "cinematic realistic OTT drama",
            "dialogue_style": "natural contemporary English",
            "pacing": "fast but readable",
        },
        "characters": [],
        "locations": [],
        "props": [],
        "episodes": [],
        "created_at": now,
        "updated_at": now,
    }


def _read_project(project_id: str) -> dict:
    path = _json_path(project_id)
    if not path.exists():
        raise web.HTTPNotFound(text="Project not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise web.HTTPInternalServerError(text=f"Invalid project JSON: {exc}")


def _write_project(project: dict) -> None:
    project["updated_at"] = int(time.time())
    path = _json_path(project["project_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _new_episode(project: dict, title: str = "Episode 01") -> dict:
    number = len(project["episodes"]) + 1
    ep_id = f"E{number:03d}"
    return {
        "episode_id": ep_id,
        "number": number,
        "title": title,
        "status": "draft",
        "synopsis": "",
        "storyboard": [],
        "shots": [],
        "selected_version_map": {},
        "created_at": int(time.time()),
    }


def _find_episode(project: dict, episode_id: str) -> dict:
    for ep in project["episodes"]:
        if ep["episode_id"] == episode_id:
            return ep
    raise web.HTTPNotFound(text="Episode not found")


def _find_shot(ep: dict, shot_id: str) -> dict:
    for shot in ep["shots"]:
        if shot["shot_id"] == shot_id:
            return shot
    raise web.HTTPNotFound(text="Shot not found")


@PromptServer.instance.routes.get("/drama_studio/health")
async def health(_request):
    return web.json_response({"ok": True, "version": "0.1.0"})


@PromptServer.instance.routes.get("/drama_studio/projects")
async def list_projects(_request):
    projects = []
    for path in sorted(PROJECTS_DIR.glob("*/project.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            projects.append({
                "project_id": data.get("project_id"),
                "name": data.get("name"),
                "updated_at": data.get("updated_at"),
                "episode_count": len(data.get("episodes", [])),
            })
        except Exception:
            continue
    return web.json_response({"projects": projects})


@PromptServer.instance.routes.post("/drama_studio/projects")
async def create_project(request):
    body = await request.json()
    project = _default_project(body.get("name", "Untitled Drama"), body.get("synopsis", ""))
    project["genre"] = body.get("genre", project["genre"])
    project["format"] = body.get("format", project["format"])
    project["episode_count"] = int(body.get("episode_count", project["episode_count"]))
    project["episode_duration_seconds"] = int(body.get("episode_duration_seconds", project["episode_duration_seconds"]))
    project["episodes"].append(_new_episode(project, "Episode 01"))
    _write_project(project)
    return web.json_response(project)


@PromptServer.instance.routes.get("/drama_studio/projects/{project_id}")
async def get_project(request):
    return web.json_response(_read_project(request.match_info["project_id"]))


@PromptServer.instance.routes.put("/drama_studio/projects/{project_id}")
async def update_project(request):
    project = _read_project(request.match_info["project_id"])
    body = await request.json()
    for key in ["name", "language", "format", "genre", "synopsis", "bible", "characters", "locations", "props", "episodes"]:
        if key in body:
            project[key] = body[key]
    for key in ["episode_count", "episode_duration_seconds"]:
        if key in body:
            project[key] = int(body[key])
    _write_project(project)
    return web.json_response(project)


@PromptServer.instance.routes.post("/drama_studio/projects/{project_id}/characters")
async def add_character(request):
    project = _read_project(request.match_info["project_id"])
    body = await request.json()
    idx = len(project["characters"]) + 1
    char = {
        "character_id": f"CHAR_{idx:03d}",
        "name": body.get("name", f"Character {idx}"),
        "age": body.get("age", 28),
        "role": body.get("role", ""),
        "personality": body.get("personality", ""),
        "speech_style": body.get("speech_style", "natural conversational English"),
        "voice_reference": body.get("voice_reference", ""),
        "image_references": body.get("image_references", []),
        "status": "draft",
        "version": 1,
    }
    project["characters"].append(char)
    _write_project(project)
    return web.json_response(char)


@PromptServer.instance.routes.post("/drama_studio/projects/{project_id}/episodes")
async def add_episode(request):
    project = _read_project(request.match_info["project_id"])
    body = await request.json()
    episode = _new_episode(project, body.get("title", f"Episode {len(project['episodes'])+1:02d}"))
    episode["synopsis"] = body.get("synopsis", "")
    project["episodes"].append(episode)
    _write_project(project)
    return web.json_response(episode)


@PromptServer.instance.routes.get("/drama_studio/projects/{project_id}/episodes/{episode_id}")
async def get_episode(request):
    project = _read_project(request.match_info["project_id"])
    ep = _find_episode(project, request.match_info["episode_id"])
    return web.json_response(ep)


@PromptServer.instance.routes.put("/drama_studio/projects/{project_id}/episodes/{episode_id}")
async def update_episode(request):
    project = _read_project(request.match_info["project_id"])
    ep = _find_episode(project, request.match_info["episode_id"])
    body = await request.json()
    for key in ["title", "status", "synopsis", "storyboard", "selected_version_map"]:
        if key in body:
            ep[key] = body[key]
    if "shots" in body:
        ep["shots"] = body["shots"]
    _write_project(project)
    return web.json_response(ep)


@PromptServer.instance.routes.post("/drama_studio/projects/{project_id}/episodes/{episode_id}/shots")
async def add_shot(request):
    project = _read_project(request.match_info["project_id"])
    ep = _find_episode(project, request.match_info["episode_id"])
    body = await request.json()
    shot_num = len(ep["shots"]) + 1
    shot = {
        "shot_id": f"{ep['episode_id']}_S{shot_num:03d}",
        "order": shot_num,
        "title": body.get("title", f"Shot {shot_num}"),
        "duration_seconds": float(body.get("duration_seconds", 8)),
        "status": "draft",
        "issue": "",
        "prompt": body.get("prompt", ""),
        "characters": body.get("characters", []),
        "location": body.get("location", ""),
        "dialogue": body.get("dialogue", ""),
        "reference_strategy": body.get("reference_strategy", "previous_frame"),
        "current_version": 0,
        "versions": [],
        "depends_on": body.get("depends_on", []),
    }
    ep["shots"].append(shot)
    _write_project(project)
    return web.json_response(shot)


@PromptServer.instance.routes.post("/drama_studio/projects/{project_id}/episodes/{episode_id}/shots/regenerate")
async def regenerate_shots(request):
    project = _read_project(request.match_info["project_id"])
    ep = _find_episode(project, request.match_info["episode_id"])
    body = await request.json()
    shot_ids = body.get("shot_ids", [])
    reason = body.get("reason", "general")
    notes = body.get("notes", "")
    jobs = []
    for shot_id in shot_ids:
        shot = _find_shot(ep, shot_id)
        old_version = shot["current_version"]
        new_version = old_version + 1
        version = {
            "version": new_version,
            "status": "queued",
            "reason": reason,
            "notes": notes,
            "created_at": int(time.time()),
            "output": None,
        }
        shot["versions"].append(version)
        shot["current_version"] = new_version
        shot["status"] = "queued"
        shot["issue"] = reason
        jobs.append({"shot_id": shot_id, "version": new_version})
    _write_project(project)
    return web.json_response({"ok": True, "jobs": jobs, "message": "Selected shots are queued in Drama Studio state. Connect the H3 adapter to render them."})


@PromptServer.instance.routes.post("/drama_studio/projects/{project_id}/episodes/{episode_id}/shots/approve")
async def approve_shots(request):
    project = _read_project(request.match_info["project_id"])
    ep = _find_episode(project, request.match_info["episode_id"])
    body = await request.json()
    shot_ids = body.get("shot_ids", [])
    for shot_id in shot_ids:
        shot = _find_shot(ep, shot_id)
        if shot["current_version"] <= 0:
            continue
        shot["status"] = "approved"
        for version in shot["versions"]:
            version["status"] = "approved" if version["version"] == shot["current_version"] else version["status"]
        ep["selected_version_map"][shot_id] = shot["current_version"]
    _write_project(project)
    return web.json_response({"ok": True, "approved": shot_ids})


@PromptServer.instance.routes.post("/drama_studio/projects/{project_id}/episodes/{episode_id}/slate/rebuild")
async def rebuild_slate(request):
    project = _read_project(request.match_info["project_id"])
    ep = _find_episode(project, request.match_info["episode_id"])
    selected = []
    for shot in ep["shots"]:
        version = ep["selected_version_map"].get(shot["shot_id"], shot["current_version"])
        if version > 0:
            selected.append({"shot_id": shot["shot_id"], "version": version})
    ep["slate"] = {
        "status": "assembled_manifest",
        "updated_at": int(time.time()),
        "shots": selected,
    }
    _write_project(project)
    return web.json_response({"ok": True, "slate": ep["slate"], "message": "Slate manifest rebuilt. Actual media assembly can be connected to FFmpeg in V0.2."})


# Placeholder node registration. This gives ComfyUI a visible integration point
# without forcing model-specific assumptions into V0.1.
class DramaStudioMarker:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project_id": ("STRING", {"default": ""})}}

    RETURN_TYPES = ("STRING",)
    FUNCTION = "mark"
    CATEGORY = "Drama Studio"

    def mark(self, project_id):
        return (project_id,)


NODE_CLASS_MAPPINGS = {"DramaStudioMarker": DramaStudioMarker}
NODE_DISPLAY_NAME_MAPPINGS = {"DramaStudioMarker": "Drama Studio Project Marker"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
