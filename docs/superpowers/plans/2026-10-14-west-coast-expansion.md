# Ting Kau / Sham Tseng Expansion Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Track completion below and in the evidence ledger.

**Goal:** Extend the existing Tsuen Wan map west along the mainland coast through Ting Kau to Sham Tseng, with a continuous exploration drive and sourced surrounding buildings.

**Architecture:** Extend the current offline government-data importers and the existing route/building/scenery pipeline. Preserve all eleven earlier routes, existing road objects and land within earlier regional boundaries. Export changed geometry through the live Blender MCP into isolated scenes.

**Tech Stack:** Godot 4.6 .NET/C#, Python regeneration tools with Shapely/pyproj, Blender MCP, existing generated facade textures.

**Spec:** User request to continue map expansion, standing request for HK government geography and metre scale, and `docs/TSUEN_WAN_EXPANSION.md` preservation and accuracy contracts. The user confirmed west along the coast toward Ting Kau and Sham Tseng.

## Global Constraints

- Runtime remains offline; no new runtime dependency.
- +X east, -Z north, one world unit per approximate metre; retain the existing projection.
- Preserve earlier roads/routes and existing coast within earlier rectangles.
- Road widths, flat terrain, facades and scenery remain explicitly authored.
- Use Blender MCP for modeling and preserve the user's Blender scene/selection.
- Build must report zero warnings and zero errors; record native and engine evidence.
- Continue the current feature checkout, retaining reviewed uncommitted Tsuen Wan changes. Do not commit, publish or discard existing work automatically.

## Review Focus

- Candidate route follows source travel directions and joins the previous endpoint without a gap or sharp reversal.
- Source coastline closes correctly without filling sea or attaching islands to mainland.
- Earlier boundaries cease blocking the new roads; every new carriageway has land and collision support.
- Regional building clips and shared heights remain consistent across the Tsuen Wan seam.
- New shortcut works only while stopped in an active game; restart restores H1 and cleans up added assets.

### Task 1: Source-derived connected map

**Files:** Modify `Tools/import_tunnel.py`, `Tools/import_shoreline.py`; create `Data/west-coast-shoreline.geojson`, `Data/west-coast-coast.json`; regenerate harbour JSON/source; evidence under `evidence/next-expansion-2026-10-14/`.

**Interfaces:** Add `WEST_COAST_BOUNDS=(-13800,-11200,-6400,-6900)` and append route index 11 from route 10's endpoint through sourced Castle Peak Road sections to Sham Tseng. Existing index 0–10 data remains unchanged.

- [x] Write and run a failing data check requiring twelve routes, route 11 endpoint X < -11700, unchanged earlier roads/routes and source-directed joins.
- [x] Select a connected source itinerary from the cached official HK1980 KMZ; obtain official coastline tiles with provenance and explicit gap records.
- [x] Extend the source importers; verify land/sea points, carriageway coverage, old-land preservation, source alignment and barrier clearance.

### Task 2: Buildings and Blender exports

**Files:** Modify `Tools/import_buildings.py`, `Tools/check_buildings.py`, `Tools/model_government_buildings.py`; create regional raw/layout JSON and GLBs; regenerate harbour and affected seam GLBs.

**Interfaces:** `--west-coast` importer flag, `WEST_COAST=True` model flag, seventh shared Kowloon building source; output `Data/west-coast-layout.json` and `Assets/Models/west-coast-buildings.glb` with additional chunk split only if needed to keep each export below 100 MB.

- [x] Write and run a failing building/model check requiring new massing, no cross-region overlaps, valid land containment and exact render/collision chunk coverage.
- [x] Download buildings atomically; generate layouts using earlier-region exclusions and shared height/base reconciliation; compare all older layouts before deciding which models need regeneration.
- [x] Export through Blender MCP; verify chunk sets, preserved tunnel/deck mesh streams, source hashes and Blender scene restoration.

### Task 3: Runtime integration and physical checks

**Files:** `Scripts/Main.cs`, `Scripts/Main.Harbour.cs`, `Scripts/Main.BuildingReview.cs`, `Scripts/Main.RestartReview.cs`, `Scripts/Hud.cs`.

**Interfaces:** `west_coast` action on O, route index 11, `--west-coast-check`, `CheckWestCoast()`, extra building asset/layout, scenery district and map labels.

- [x] Add a failing in-engine check for O shortcut and route 11, then implement the action, notices, scenery and building loading.
- [x] Validate shortcut guards, full-bus envelope clearance, route support and a physical drive along the complete new itinerary.
- [x] Add a restart cycle from the new drive; capture native street, seam, coast and map views with actual key-event dispatch.

### Task 4: Full verification, attribution and final review

**Files:** `README.md`, `docs/PLAN.md`, `docs/GOVERNMENT_BUILDINGS.md`, new `docs/WEST_COAST_EXPANSION.md`, evidence and manifests.

- [x] Run the building downloader/shared-height regression, full in-engine suite and restart checks; inspect every result and final native images.
- [x] Document exact counts, source dates/hashes, preservation evidence, generated asset use and approximations.
- [x] Request one fresh whole-expansion review, resolve actionable findings and record final file/log hashes. The independent reviewer identified the turn failure and label issue, but its final assessment was interrupted by a service usage limit. Remaining review was completed locally; no independent final sign-off is claimed.

No merge or publication step is part of this request.
