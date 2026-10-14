# Cheung Sha Wan / Lai Chi Kok Expansion Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans in this session; perform one fresh-context final review. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Extend the connected Kowloon map north and west from Sham Shui Po through Cheung Sha Wan to Lai Chi Kok, with a physically drivable exploration route.

**Architecture:** Extend the existing offline government-data importers and isolated Blender generators. Preserve earlier road/source snapshots, routes and tunnel profiles; add a separate northwestern building/coast extract and merge its land at the existing boundary. Reuse the current scenery, HUD, physics and check cascade.

**Tech Stack:** Godot 4.6 .NET / C#, Python with installed Shapely/pyproj for regeneration, Blender MCP, TD centreline KMZ and LandsD CSDI data.

**Spec:** User request in this chat: continue the map expansion, choosing “North toward Cheung Sha Wan / Lai Chi Kok”. Existing source/accuracy contracts: `docs/GOVERNMENT_MAP_FIXES.md` and `docs/WEST_KOWLOON_EXPANSION.md`.

## Global Constraints

- Preserve all 2,990 existing road polylines, eight routes, both tunnel profiles and H1 data.
- Government horizontal geometry is authoritative; widths, elevations, terrain, furnishings and the new exploration itinerary remain authored.
- Runtime stays offline; use existing dependencies and generated art.
- Export through Blender MCP and restore the user's scene and selection.
- Keep the latest raised-join, portal, building-height and map-projection corrections.
- No commits, publication, new passenger service or additional signal simulation in this task.

## Review Focus

- Datum or stable-ID mismatch must not shift old roads; compare every retained road/source record.
- Boundary joins must remove internal fences, retain the old coast and keep new carriageways on land.
- Regional building footprints must not overlap; touching roof parts must retain consistent height inputs.
- The new route must respect source direction, reach Lai Chi Kok and physically drive without contacts or departures.
- The new shortcut must obey stopped/paused/map guards; expanded HUD labels must remain readable.

### Task 1: Government geometry and preservation

**Files:** `Tools/import_tunnel.py`, `Tools/import_shoreline.py`, new `Data/lai-chi-kok-{shoreline,coast}.json/geojson`, existing harbour outputs; evidence in `evidence/lai-chi-kok-expansion-2026-10-12/`.

**Interfaces:** New `NORTHWEST_BOUNDS=(-4600,-6000,0,-3900)` and `--northwest` shoreline mode; retain existing modes. Add a ninth source-ID route after selecting a direction-valid continuous path in the downloaded network.

- [x] Save pre-expansion code/data/models and SHA-256 manifest.
- [x] Add and observe a failing evidence check for new geographic coverage and a connected ninth route while pinning all earlier road/route/source data.
- [x] Download official source data with provenance; add the region, retained-coast merge and explicit route using the current projection.
- [x] Run importer assertions and the preservation/land/route audit; record counts and source hashes.

### Task 2: Buildings and Blender geometry

**Files:** `Tools/import_buildings.py`, `Tools/model_government_buildings.py`, new northwestern layout/GLBs; regenerated harbour GLB and editable sources.

**Interfaces:** Add `build(..., northwest=False)` / `--northwest`, and Blender `NORTHWEST=True`; reuse 128 m chunks and facade atlases. Import all Kowloon snapshots for consistent shared building datums and height inputs.

- [x] Add a failing coverage/seam check for the new region.
- [x] Download a count-checked building extract; derive new footprints excluding existing regions and road clearances. Rebuild earlier layouts only where shared height/clearance reconciliation requires it.
- [x] Export changed models through Blender MCP; verify exact chunk coverage, source preservation and no building overlaps.

### Task 3: Runtime integration and physical route

**Files:** `Scripts/Main.Harbour.cs`, `Scripts/Main.BuildingReview.cs`, `Scripts/Main.cs`, `Scripts/Hud.cs`.

**Interfaces:** Append route index 8; action `northwest` on N while stopped; `--northwest-check` focused route check; existing full suite includes the ninth route.

- [x] Add failing in-engine coverage, shortcut-guard and route assertions.
- [x] Load new building chunks; distribute existing lamps/trees/passenger decorations into the extension; add map labels and credits.
- [x] Run the focused check and inspect native street, seam, coast and HUD captures; fix any physical or visual failures.

### Task 4: Final validation and documentation

**Files:** `docs/LAI_CHI_KOK_EXPANSION.md`, `README.md`, evidence logs/captures/manifest.

- [x] Run importer regressions, preservation audits and the full `--self-test`; require exit 0, `ANTILA_SELF_TEST_OK`, 0 build warnings/errors and all existing routes/H1 passing.
- [x] Run restart validation for new assets and repeatable scene construction.
- [x] Obtain a fresh-context final review of the expansion against the saved baseline; address correctness findings with focused regression evidence.
- [x] Record exact sources, dimensions, route access, results, approximations and remaining limits.

## Execution ledger

- Baseline: `eb81d31c739953be2d494fba6a1531c5820d18ee`, plus existing uncommitted map work. Snapshot saved in `Art/before-lai-chi-kok-expansion-2026-10-12/`; 26 baseline data/building hashes recorded.
- Ruling: Continue in the existing checkout on `codex/lai-chi-kok-expansion` because the user's active map and Blender scripts use this absolute workspace path. Preserve all earlier changes and use the saved snapshot as the expansion review boundary; no commit or publication is requested.
- Pre-flight: shoreline output feeds road land clipping; road output feeds building clearance and runtime. New building mode must participate in shared height reconciliation. All outputs remain compatible with the current single-scene runtime.

- RED: `check-data.py` exited 1 with “Lai Chi Kok road coverage missing”; `check-buildings.py` exited 1 with “Lai Chi Kok building layout missing”.
- Source preflight: official 125,565,141-byte centreline KMZ downloaded (initial 120-second timeout resumed successfully); SHA-256 `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`. New building download: 4,504 records; 1,895 shared western identities have unchanged height inputs. Shoreline: 114 source fragments, 904 m of coastline inside the added rectangle; importer exited 0.
- Route selected: 31 direction-valid source sections, about 2.925 km, from the existing Sham Shui Po endpoint along Lai Chi Kok Road, Butterfly Valley Road, Cheung Sha Wan Road and Mei Lai Road to its Lai Wan Road junction.
- Ruling: Add a 16K surface-mask dimension guard because the planned extent requests a 16,460-pixel-high texture at the existing resolution. This changes pixel density only beyond the cap; world-coordinate placement is retained. A failing in-engine boundary regression is running before the implementation.

- Task 1 complete: importer and independent data audit exited 0; 445 new / 3,435 total roads; nine routes; 7,172,689.56 m² new land. All 2,990 prior roads, eight prior routes, tunnel profiles, pinned source records and old western land footprint are unchanged.
- Building imports all exited 0: 2,799 new parts; original and northern layouts retain identical building/paving arrays. Western clearance reconciliation affects 84 existing source IDs and removes two; 11 heights change because the expanded connected groups supply lower base datums. The prior height-refresh regression remains green.
- Blender MCP exports completed for the harbour, three northwestern building GLBs and four western seam GLBs; original scene/objects/selection/active object restored.
- RED→GREEN mask gate: pre-fix `--map-check` exited 1 on the 16K limit; the later runtime run passed this gate and failed exactly at the unwired N shortcut. N/scene integration has now been implemented; focused check passed.

- Task 2 complete: all source hashes, 1,403 chunk pairs and 158 shared building-height identities pass; 267 existing tunnel/deck mesh streams preserved exactly.
- Task 3 focused gate: `--northwest-check` exited 0, 2,910 m physically driven without contacts/departures; N shortcut and four guards pass. Full suite running; native captures and restart remain pending.

- Full `--self-test` exited 0 with `ANTILA_SELF_TEST_OK`: 16 harbour drives (nine routes plus seven focused drives), two side-street turns, original H1 three stops / 26 passengers; 0 warnings / 0 errors. Native captures running; independent final review dispatched as required by the execution skill.

- Native capture exited 0; N input event and all eight rendered views pass. Visual inspection found the expanded street network close to the Sham Shui Po map label; moved its label offset 45 logical pixels left. Final capture after this text-only adjustment remains pending.

- Final independent review: no concrete correctness/regression findings; condition is completion of restart and final post-label native capture. No minors deferred and no fix pass required.
- Final: Ruling: Survey-grade elevations/widths/terrain/furnishings set aside by reviewer — retain documented authored approximations; a real-world reconstruction would require more source data/modeling.
- Final: Ruling: New passenger services/signals/traffic routing/animation set aside — remain outside this map expansion; the new district supports exploration while H1 gameplay remains unchanged.
- Final: Ruling: Performance benchmarking set aside — no performance claim; native rendering/reload validation does not establish frame-time/memory performance on other hardware.

- Verification issue: initial restart run exited 0 but printed the OLD three-reload marker. The restart source was saved during the preceding build and predates its DLL timestamp, so incremental build reused the stale assembly. Retained as `restart-stale-build.log`; NOT accepted as the four-reload gate. Force a nonincremental build and rerun final restart/capture checks.

- Corrected restart gate exited 0: all four reloads, including northwest drive, restore H1 with 2,806 meshes / 1,403 collision shapes; all five scenes pass 519 roof probes and 2,281 paving samples. Four-reload marker confirmed; no engine errors. Final post-label native capture now running.

- Task 3 complete: final native capture exited 0 on the rebuilt assembly; N input and all eight views pass. Inspected revised map: Sham Shui Po text is clear of the road network.
- Task 4 complete: required data/model/importer/full-simulation/restart/native gates all pass; independent review has no findings or deferred minors. Exact results and SHA-256 manifests retained in evidence; all changes remain local and uncommitted as planned.
