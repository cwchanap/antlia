# Wong Tai Sin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Extend the connected eastern driving world from Kowloon City to Wong Tai Sin with government-derived roads/buildings and verified offline assets.

**Architecture:** Extend the existing east land/building region inside unchanged world bounds. Append exploration route 13 and a Y shortcut while preserving routes 0–12 and scheduled services. Reuse the existing source, modeling, clearance and physics-test pipelines.

**Tech Stack:** Godot 4.6 .NET/C#, existing Python/Shapely geodata environment, isolated Blender MCP exports, current generated textures and props.

**Spec:** `docs/superpowers/specs/2026-10-24-wong-tai-sin-design.md`

## Global constraints

- Local X east, −Z north, approximately one metre per unit; no DEM or surveyed-grade claim.
- East selection `(550,-6400,3150,-100)`; retain world bounds `[-13880,-11280,3230,2150]`.
- Preserve the existing 6,671 roads/source records, thirteen exploration drives, two tubes and H1/H2/H3.
- Use one existing east source/layout; leave the 42-fragment sports inventory intact.
- Modeling runs only through Blender MCP and restores the user's scene.
- Every shell command begins with `rtk`; use Godot Mono. Preserve unrelated dirty work and leave delivery uncommitted.

## Review focus

- Broken road joins/directions: source itinerary must be connected and government-directed before modeling.
- Lost old data: compare every prior road/source record, route and tube with the baseline.
- Incomplete/overwriting building refresh: validate count/IDs/geometry before merge and retain all old source features.
- Mismatched collision/visual exports: validate actual GLB streams against their layout and preserve old tunnel/deck streams.
- Mask/boundary/shortcut regressions: retain world size, probe the new edge, drive the route physically, and test Y guards and old services.

### Task 1: Source roads and land

**Files:** `Tools/import_tunnel.py`, `Tools/import_shoreline.py`, new `Tools/check_wong_tai_sin.py`, `Tools/check_east_kowloon.py`, east coast and cross-harbour Data outputs.

**Interface:** Produce the extended eastern land in the existing schema, appended road/source records, and route index 13 with explicit signed `source_ids`, name and sampled points. Preserve routes 0–12. Report total/new road count and route length for runtime assertions.

- [x] Add a failing focused source check requiring a fourteenth route reaching Wong Tai Sin Road, correct joins/directions/support and baseline parity; record RED on current data.
- [x] Extend only the inland east boundary; preserve actual shoreline fragments and old land within the previous cut.
- [x] Select connected source roads and a directed itinerary from the prior eastern endpoint. Regenerate safely and verify all prior arrays/records remain unchanged.
- [x] Pass source geometry, scale, boundary, support and preservation checks; freeze outputs for the building task.

### Task 2: Buildings and modeling inputs

**Files:** `Tools/import_buildings.py`, `Tools/model_government_buildings.py`, `Tools/check_buildings.py` if needed, eastern raw source and affected building layouts.

**Interface:** Extend `east-kowloon-buildings.geojson` without losing old records. Emit updated nine layout files, a geometry-change manifest, and a fourth eastern export named `wong-tai-sin-buildings` for chunks north of the old region. Existing model modes remain compatible.

- [x] Add a regression proving a northern merge preserves old source features and rejects incomplete source responses before replacement.
- [x] Download validated government coverage, merge only additional northern records with recorded provenance, and preserve old footprints/attributes.
- [x] Rebuild the eight Kowloon layouts against Task 1; compare building/pavement arrays before deciding which GLBs need regeneration.
- [x] Prepare the isolated fourth-GLB split at an existing 128 m chunk boundary; keep all exports below 100 MB.

### Task 3: Runtime integration

**Files:** `Scripts/Main.WongTaiSin.cs` (new), `Main.cs`, `Main.Harbour.cs`, `Main.BuildingReview.cs`, `Main.Routes.cs`, `Hud.cs`, `Main.RestartReview.cs` as required.

**Interface:** Y / `wong_tai_sin` starts route 13 with existing guards; `--wong-tai-sin-check` selects its physical drive. Include new checks in the existing full suite and add the new building GLB to the east asset group.

- [x] Add checks for the route endpoint, source-supported lanes, northern boundary, district density and Y's stopped/map/pause/completion guards using existing test patterns.
- [x] Wire the shortcut, HUD credit/label/help, new model and regional scenery; retain P and services unchanged.
- [x] Update pinned road/route/building counts from the verified Task 1/2 outputs and check label overlap through existing route checks.

### Task 4: Assets, integration and delivery

**Files:** Shared harbor and changed building GLBs/blends, derived open-space layouts if hashes change, README, `docs/WONG_TAI_SIN_EXPANSION.md`, evidence folder.

- [x] Through Blender MCP, export the harbor model and changed building regions; inspect generated geometry and verify preserved tunnel/deck streams.
- [x] Refresh clearance-input metadata and run the existing park/source checks, preserving park sports/fittings unless actual geometry changes require repair.
- [x] Run .NET build with 0 warnings/errors; import assets; run focused WTS checks and the complete headless fixed-60 self-test.
- [x] Capture and inspect native overview, approach, Wong Tai Sin street/arrival, boundary and service/shortcut evidence.
- [x] Obtain a fresh independent whole-feature review, resolve concrete findings and save preservation/source/test records.
- [x] Update docs/credits and report exact completed checks and unrun gates. No commit, PR or publication is requested.
