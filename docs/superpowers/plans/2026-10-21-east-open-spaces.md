# Eastern open spaces implementation plan

**Goal:** Fill the nine reviewed park/waterfront gaps using verified government site and sports outlines, preserving all existing roads, buildings, routes and Mong Kok recreation.

**Architecture:** Reuse the existing offline recreation JSON, Blender sports model and terrain-mask conventions. Export a separate eastern recreation asset; merge both regions' surface triangles into the existing recreation mask and add eastern paving before street meshes finish. Paths, planting and fittings are authored within source boundaries; this is not a surveyed garden or heritage reconstruction.

**Scope:** Hutchison Park, Tai Wan Shan Park, Hoi Sham Park, Ko Shan Road Park, To Kwa Wan Recreation Ground, Kowloon Walled City Park, Carpenter Road Park, Kowloon Tsai Park and the reviewed Hung Hom Harbourfront site. No new map extent or bus service.

## Source and asset work

- [x] Refresh official iB1000 index/archive evidence, retain hashes and revision dates, and compare selected site/sports geometry with the reviewed snapshot. Reject incomplete inputs before replacing outputs.
- [x] Add failing offline checks for nine site boundaries, usable paths/furniture, source-derived sports surfaces, clearance and old-data preservation.
- [x] Produce `Data/east-kowloon-open-spaces-source.geojson` and `Data/east-kowloon-open-spaces.json` with the established `sites`, `surfaces`, `paving`, `fixtures`, `sports`, `gardens`, `play_areas` schema. Garden entries carry source `rings`, authored `paths`/`access`, and paving `samples` for all nine sites. Use all loaded building layouts and current mainland land/roads for clipping; keep adjacent/overlapping sites and multi-tile sport IDs from duplicating fixtures.
- [x] Reuse `Tools/model_open_spaces.py` with an explicit region option to export `Assets/Models/east-kowloon-recreation.glb` and `Art/east-kowloon-recreation.blend` through Blender MCP. Restore the user's previous Blender scene; preserve existing Mong Kok outputs byte-for-byte.

## Runtime integration and verification

- [x] Reproduce the missing eastern paving/sports/detail behavior in the engine, then load the new asset/data after Mong Kok recreation and before harbour decoration.
- [x] Merge both regions' recreation surfaces into the existing mask; preserve Mong Kok play-pad behavior and geometry. Add eastern path triangles to paving and reserve new surfaces against later decoration.
- [x] Add engine checks for every site's path samples, surface channels, source-contained furniture, building/road/stop/entrance clearance, sport collision and ground support. Include them in full self-test and focused scenery checks.
- [x] Run offline source/preservation checks, a warning-free build, the full in-engine suite, native captures at the nine saved review cameras, and independent review. Resolve concrete failures and inspect all images.
- [x] Update source attribution and companion documentation; save before/after gallery and exact evidence/limits. No commit or PR requested.

## Review focus

Partial tile refreshes must preserve old bytes. Paths must reach source edges without obstructing roads/stops. Planting and goals must stay out of paths and playing areas. Shared source IDs and overlapping parks must not double model surfaces. The existing Mong Kok masks, fittings and services must remain intact. Feature revision/WIP annotations must remain visible in provenance.
