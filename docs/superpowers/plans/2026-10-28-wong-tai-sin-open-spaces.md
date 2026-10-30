# Wong Tai Sin open-space fill implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute the approved correction.

**Goal:** Fill the seven reviewed government-bounded park sites and their 33 sports outlines within the existing map.

**Architecture:** Extend the existing eastern open-space selection and its exact source-fragment inventory. Reuse its safe-area, path, entrance, planting, sports-fitting and Blender export pipeline. The game continues to load one offline eastern recreation dataset and asset.

**Tech Stack:** Godot 4.6 C#, Python/Shapely regeneration tools, live Blender MCP.

**Spec:** `evidence/government-gap-review-2026-10-27/review.md`, authorized by the user's “Go ahead for the fix”.

## Global Constraints

- Add source sites 1503005853 (Morse Park), 1503005716 (Junction Road Park), 1503005939 (Choi Hung Road Playground), 1503005718 (Lion Rock Park), 1910059822 (Diamond Hill Water Feature Park), 1503005810 (Ma Chai Hang Recreation Ground), and 1503005961 (Fung Tak Park).
- Preserve all nine earlier eastern sites, 38 sports IDs and 42 reviewed sports fragments. The combined selection has 16 sites and 71 unique sports IDs. Validate complete new cross-sheet patches, including multiplicity, before replacing saved files.
- Preserve existing roads, buildings, coast, terrain bounds, services and unrelated dirty work. Do not commit, push, or replace other generated models.
- Use the reviewed official northern ZIPs and recorded hashes. Source boundaries and sports geometry are government-derived; paths, entrances, surface styling, furniture and planting remain authored. Do not claim whole-venue dimensions or present-day venue access.
- Model only through Blender MCP, keeping its isolated scene/export/restoration contract. Runtime stays offline; no new dependencies, image assets, DEM, pools or heritage reconstruction.

## Review Focus

- A surviving sports ID with a missing sheet patch must reject without changing source/layout files.
- Existing site/sports geometry must survive the additional selection; source identity must remain traceable to exact sheets and hashes.
- Park paths must connect to public pavement while staying clear of roads, buildings, playing surfaces and service stops.
- Recreation masks, source inventories, in-engine checks and actual model/collision counts must agree after expansion.
- Native evidence must show the new parks without HUD obstruction and retain readable map views; saved logs alone do not prove new execution.

### Task 1: Extend and verify the existing recreation layer

**Files:** `Tools/import_east_open_spaces.py`, `Tools/check_east_open_spaces.py`, `Data/east-kowloon-open-spaces-source.geojson`, `Data/east-kowloon-open-spaces.json`, `Scripts/Main.EasternOpenSpaces.cs`, dependent exact-count checks/credits, `Art/east-kowloon-recreation.blend`, `Assets/Models/east-kowloon-recreation.glb`, `docs/EAST_KOWLOON_OPEN_SPACES.md`, `docs/WONG_TAI_SIN_EXPANSION.md`, `README.md` and task evidence.

**Interfaces:** Consume the reviewed sources under `evidence/government-gap-review-2026-10-27/` and `/private/tmp/antila-gov-gap-review-2026-10-27/north-official-tiles/`. Produce the same JSON/GLB formats already consumed by `BuildEasternOpenSpaces()`; add no alternate runtime path.

- [x] Add a failing coverage check for the seven source IDs and their 33 sports IDs, and a failing partial-fragment refresh case for a new multi-sheet sport.
- [x] Extend the reviewed inventory/manifest and source extraction while preserving existing source geometries and strict replacement validation; regenerate the layout using existing placement rules.
- [x] Update all affected runtime assertions/credits and source documentation from actual generated counts. Verify deterministic rebuild, source preservation, rejected refreshes and build with 0 warnings/errors.
- [x] Rebuild only the eastern recreation model through Blender MCP, preserving the user's scene, and validate fitting/collision correspondence.
- [x] Run the full in-engine suite and native matched before/after park captures, inspect the actual images and record evidence. Address concrete failures without relaxing clearance/fragment guards.
- [x] Obtain a fresh independent spec/quality and whole-change review, resolve actionable findings, and record final hashes and material unrun gates.

The existing feature checkout is the delivery workspace. Its heavily dirty map/assets are prerequisites and remain in place. Local uncommitted delivery follows the user's ongoing workflow; no new branch or publication is needed.
