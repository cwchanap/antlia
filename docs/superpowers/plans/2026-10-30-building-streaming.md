# Building streaming implementation plan

**Goal:** Reduce the expanded city's resident memory by loading detailed buildings and their collision only near the bus.

**Approved direction:** The user approved nearby building/collision streaming after the measured 8.32 GiB startup peak. The first deliverable is building streaming; props, tiled terrain and a separate menu scene remain later work. The 2–3 GiB driving / below 4 GiB peak figures are targets to measure, not promised results.

**Architecture:** Repack the existing 128 m building pairs without changing geometry, UVs or government data. Each independent GLB references three shared textures. Keep collision-derived low-detail massing globally for the distant skyline. Load detail within 1,000 m, retain it to 1,500 m, and prepare teleport destinations before moving the bus. Background requests prepare newly approached chunks; real colliders must exist around the bus before physics continues.

**Constraints:** Offline runtime, Godot 4.6 .NET / GL Compatibility, no new dependencies or test project. Preserve existing local fixes, all source models, placement order, data provenance and `QuitGame` cleanup. Conservative actual mesh bounds cover geometry beyond a chunk's nominal cell. Use this checkout and leave changes local.

## Tasks

- [x] Package independent chunks and shared textures with a deterministic standard-library tool. Check exact source/accessor payload equivalence, bounds, materials, source hashes and all 3,135 pairs; generate lightweight distant proxies.
- [x] Add a building-streaming partial and destination callback in `BusController.ResetAt`. Dispose scene/resource ownership on eviction and reload; adapt building checks, global roof probes, district readiness, reload checks and captures to residency.
- [x] Add an in-engine `--streaming-check`: bounded initial residency, near colliders, conservative boundary selection, background approach, distant eviction/resource release and teleport/return. Run it red against the old eager world, then green.
- [x] Run full real-physics checks, native building/render checks, native captures and reload checks; measure normal `just run` physical footprint plus driving/teleport memory, and inspect captures. Obtain a fresh final review and resolve actionable issues.
- [x] Update startup/building docs and record measured results, tradeoffs and remaining costs in `evidence/building-streaming-2026-10-30/`.

## Review focus

Chunk overhang and negative coordinates; slow/failed background loads; obsolete in-flight requests after teleport; C# wrappers retaining evicted meshes; captures/roof checks outside the active window; scene reload while requests are outstanding. Tests must exercise these paths without loading the entire detailed world at once.

## Measured scope adjustment

Building streaming passed but normal startup still peaked at 7.04 GiB. Temporary per-stage native profiling located another large allocation in the three HUD map canvases: they submit 456,506 road/coast segments, including every off-screen district in route previews. Drawing all three adds about 647 MiB of persistent native geometry and about 1,005 MiB of rendering buffers on the first frame. The implemented map-only change simplifies lines within 0.35 physical output pixel and conservatively rejects off-screen route-map segments; roads, collision, service paths and styles retain their existing authority. Synthetic geometry checks, actual route-map coverage, native render-buffer and 2x resize checks passed. Native buffers fell from 1,180.2 MiB in the red run to 220.2 MiB initially and 246.2 MiB after resizing. This extended the approved memory fix based on measured residual cost.

## Final outcome — 31 October 2026

All seven final engine/capture/reload/startup gates passed, and all 19 final captures were independently reviewed. The normal recipe reached the menu in 42.44 s, with 5,481.55 MiB sampled peak physical footprint and 5,479.90 MiB at the live idle menu, down 35.66% / 31.95% from the earlier completed eager-world run. Native rendering used the unchanged 1280 × 800 viewport with a temporary unfocused screen-edge window placement; natural drawing was verified and the override was removed afterward. These local observations are not a benchmark.

Full self-test: 25 exploration drives, 133,749 clearance probes, H1/H2/H3 and the original 1.08 km service. Reload suite: nine reloads / ten validated states, each with 82 detailed chunks and matching collision shapes. Final source, assembly and shared texture/import hashes are recorded in `evidence/building-streaming-2026-10-30/validation.json`; the report records the red/green loader, mipmap and renderer regressions.

The below-4 GiB peak target remains unmet; a 2–3 GiB steady-driving budget has not been demonstrated. Props and terrain remain global. Manual desktop keyboard play was not checked.
