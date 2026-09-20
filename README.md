# Drama Studio — ComfyUI V0.1

A production-control extension for building AI microdramas in a stateful, shot-based workflow.

## What V0.1 does

- Persistent project/series state under ComfyUI output storage.
- Project → Bible → Characters → Episodes → Shots structure.
- Character IDs and versionable metadata.
- Shot-level versioning.
- Selective regeneration: regenerate only selected shots.
- Shot approvals.
- Episode slate manifests that point to approved/current shot versions.
- A ComfyUI frontend panel and launcher.
- A minimal backend API for future model/workflow adapters.

## Install

1. Stop ComfyUI.
2. Copy this whole `DramaStudio` folder into:
   `ComfyUI/custom_nodes/DramaStudio/`
3. Start ComfyUI again.
4. A **Drama Studio** launcher appears in the top-right.

The extension uses ComfyUI's standard `WEB_DIRECTORY` mechanism and `app.registerExtension()` frontend registration. See the official ComfyUI extension documentation for the current extension-loading model.

## V0.1 limitations

This first build intentionally separates **production state/orchestration** from model execution. The H3/Qwen/TTS/MuseTalk workflows are not hard-coded yet. This prevents us from coupling the data model to a single node graph while we are still finalizing the exact workflows.

Next adapter stage:

- H3 Ref2VA shot compiler and render queue
- Qwen-Image character generation
- Qwen-Image-Edit character locking/variants
- Qwen3-TTS voice generation
- MuseTalk lip sync
- Whisper timestamps
- FFmpeg assembly

## Data location

Project state is stored under:

`<ComfyUI output>/drama_studio/projects/<PROJECT_ID>/project.json`

## Shot regeneration rule

A regeneration creates a new shot version. Other shots are not mutated. Episode assembly references the approved/current version map, so a regenerated shot can replace only itself in the final slate.

## Security note

The V0.1 backend validates IDs and writes only inside the Drama Studio data directory below ComfyUI's output directory. No arbitrary filesystem write API is exposed.
