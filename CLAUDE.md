# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**Grand Theft Mole**: a mobile (iOS/Android) online multiplayer social-deduction game. A heist crew in a GTA 2-style top-down tiny Amsterdam has to find the undercover cops (Moles) among them. Round-based lobbies of 6–12 players, proximity voice.

**[GDD.md](GDD.md) is the source of truth for game design.** Read the relevant section before implementing a feature. If an implementation decision changes the design, update GDD.md in the same change.

## Stack

- **Client:** Godot 4, GDScript (not C#). Mobile-first: touch controls, portrait-safe UI anchoring, landscape gameplay.
- **Backend:** Nakama (auth, matchmaking, wallet, storage), run locally via Docker Compose.
- **Game server:** server-authoritative. Headless Godot build sharing gameplay code with the client (not yet final, see GDD §15/§17).
- **Rendering:** 3D world with 2D art, GTA 2 style. Box buildings with roof/wall textures, flat top-down sprites for characters and vehicles, a perspective camera looking straight down. Gameplay logic is 2D on the ground plane (x/y); only rendering is 3D.
- **Art:** pixel art via low-resolution rendering (GDD §14; current line-art assets are placeholders), generated with Nano Banana Pro via Magnific by the user, then processed by our pipeline scripts.

## Rules that matter

- **Server authoritative.** Clients send inputs, the server decides positions, hits, kills, votes, job completion, Heat and money. Never trust a client-reported outcome.
- **Never leak hidden roles.** The server must not send role data to non-Mole clients (not in match state, player lists, debug info or RPC payloads). Moles get their teammates' identities, and nobody else gets anything.
- **Money is server-only.** Wallet changes happen only in Nakama server code.
- **Prediction:** clients predict their own on-foot movement and driving, and interpolate everyone else. Keep simulation code deterministic enough to share between client and server.
- **Mobile performance:** test against mid-range phones. Watch draw calls, physics body counts and the AI civilian/traffic budget.

## Conventions

- GDScript with static typing (`var speed: float = 120.0`, typed function signatures).
- Files and folders: `snake_case`. Classes (`class_name`): `PascalCase`. Signals: past tense (`job_completed`).
- One scene per reusable thing, and the script sits next to its scene.
- Keep Godot scene/resource files as text (`.tscn`, `.tres`) so they diff and can be edited directly.
- Art files go through Git LFS (see `.gitattributes`). git-lfs is installed user-locally in `~/.local/bin` and enabled with `git lfs install --local`.

## Art pipeline notes

- Raw generations go in `art/raw/`; processed, game-ready files go in `assets/`. Never hand-edit `assets/` files that the pipeline generates.
- Raw file names: `<category>_<subject>_<NN>`, with category one of `tex_`, `sprites_`, `facades_` (references: `style_anchor.png`, `mood_*.png`; `mood_pixel_street.png` is the pixel-art style reference). Rename Magnific downloads to this scheme.
- Pipeline: add the raw file to `tools/art_pipeline/manifest.json`, then run `.venv/bin/python tools/art_pipeline/process_art.py` (setup: `python3 -m venv .venv && touch .venv/.gdignore && .venv/bin/pip install -r tools/art_pipeline/requirements.txt`). It writes `assets/art_manifest.json` with real-world sizes at 64 px per metre.
- Sprites face up (forward = up in the image). Use `rotate` in the manifest to fix ones that don't.
- Ask for orthographic parts only (roofs from straight above, facades straight-on, seamless ground, top-down sprites). Don't attach the style anchor when generating sprites; the model copies it into the image.
- Tall thin props (lamp posts, railings, bollards) and roofs are simple 3D geometry, not sprites. Roofs use the `roof_tiles` texture.
- Characters and vehicles are single top-down sprites rotated in-engine, so there are no directional sheets. Characters use a cutout rig (separate body parts).
- World art must be neutrally lit; mood lighting is done at runtime. Emissive parts (signs, windows, headlights) are separate masks.
- Player identity comes from colour and silhouette (faces aren't visible from above). Faces appear only in UI portraits.

## Magnific MCP

The Magnific MCP is connected, but the user's unlimited generations work only in the Magnific app, not through the MCP. Don't generate art through the MCP without asking, because it may cost credits. The user generates art in the app and drops the files into the project for processing.

## Running the game

- Godot is at `/Applications/Godot.app` (4.7.2). Binary: `/Applications/Godot.app/Contents/MacOS/Godot`.
- Import after adding assets: `Godot --headless --path . --import`.
- The current main scene is `scenes/test/canal_block_test.tscn`. It can save a screenshot and quit, which is how to check rendering without the user: `Godot --path . -- --screenshot=/abs/path.png --pixel=4 --height=40 --night` (pass each flag as a separate argument). macOS has no `timeout`; use `perl -e 'alarm 60; exec @ARGV' Godot ...`.
- Commit `.import` and `.uid` files; `.godot/` is ignored.
