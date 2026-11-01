# Building streaming — 30 October 2026

Detailed buildings load around the bus instead of retaining every district model. The existing 3,135 render/collision pairs are independent assets. Selection uses their actual world-space mesh bounds, including buildings extending beyond nominal 128 m cells. Detail loads within 1,000 m and remains until 1,500 m to avoid repeated loading at the edge. Up to eight background requests prepare approaching chunks; at most two completed chunks are instantiated per physics tick. A synchronous 250 m critical window prevents physics from outrunning collision loading.

Every `BusController.ResetAt` prepares the destination before changing position, covering route previews, service starts and exploration shortcuts. Reload cleanup drains pending requests, frees detailed nodes and disposes their owned mesh/material/shape wrappers. Three shared facade/shopfront textures survive chunk eviction. Global road, roof and stop checks prepare their probe regions; camera-only captures prepare the viewed region. Checks continue to use real imported collision, with no all-city detail mode.

Low-detail skyline proxies remain globally resident and use the original collision wall/roof geometry without physics or textures. Each proxy hides while its detailed counterpart is resident. Distant storefronts, facade colours, parapets and rooftop fittings are intentionally omitted from these proxies. The government footprint/height data, detailed vertices, UVs, materials and collider geometry remain unchanged.

## Regeneration

After exporting changed government building models through Blender MCP, run:

```sh
python3 Tools/split_building_chunks.py
python3 Tools/split_building_chunks.py --self-test
python3 Tools/split_building_chunks.py --check
./run.command --headless -- --streaming-loader-check
./run.command --headless -- --streaming-check
```

The standard-library packer copies existing glTF accessor payloads without remodelling. `Data/building-chunks.json` records source SHA-256 values, per-chunk bounds and paths. Its `--self-test` and `--check` validate source hashes, pruned resource references, exact attribute/index payloads, transforms, UV/material equivalence, proxy geometry and all three shared PNG import configs. Regenerated `.import` configs preserve mipmaps and lossless PNG compression (`compress/mode=0`); a fresh Godot import accepted the three textures. The 23 original source GLBs stay available for offline regeneration; the runtime uses only the independently packaged assets. Python and Blender are not runtime dependencies.

Packaged detail is 1,074,387,480 bytes, skyline proxies 105,782,192 bytes and the three shared PNGs 7,421,615 bytes. This adds derived assets alongside the original offline source models; it trades disk space for independently releasable runtime resources.

## Verification and memory

The focused engine check covers bounded starting residency, negative bounds/cell edges, distant teleports, real roof collision, destroyed nodes and disposed mesh ownership, background loading, obsolete requests and return to H1. The full self-test includes it.

Godot 4.6.2's headless dummy renderer has a non-thread-safe mesh RID allocator, so headless streaming checks load nearby detail on the main thread. Normal native play retains background chunk requests ([dummy allocator](https://github.com/godotengine/godot/blob/4.6.2-stable/servers/rendering/dummy/storage/mesh_storage.h#L50), [GLES allocator](https://github.com/godotengine/godot/blob/4.6.2-stable/drivers/gles3/storage/mesh_storage.h#L252)). An initial full headless attempt hit nine engine errors after 626 seconds, 133,749 clearance queries and 11 drives; see the retained [failed-run log](../evidence/building-streaming-2026-10-30/self-test-final.log). After the headless loading workaround, the final `--self-test` passed in 1,052.23 seconds with 25 exploration/approach drives, all 133,749 clearance probes, H1/H2/H3 (15 stops / 119 passengers) and the original 1.08 km service. See the [clean test log](../evidence/building-streaming-2026-10-30/self-test-clean.log).

All seven final gates passed without engine errors. The native building check passed 985 roof probes, 72 rendered boundary probes, footpaths, materials and the mipmap assertion. Before the importer-config fix, `CheckBuildings` caught missing mipmaps; the [red assertion log](../evidence/building-streaming-2026-10-30/mipmap-red.log) is retained. The packer self-test and `--check` now pass, and the fresh import retained mipmaps on all three shared textures.

The native map resize check passed at 220.2 MiB initially and 246.2 MiB at 2880 × 1800; these are renderer buffers, not process physical footprint. Nine reloads restored ten validated states with 3,299 mesh nodes (including 3,135 skyline proxies), 82 detailed render/collision pairs and 82 collision shapes per state. All 19 final captures passed independent visual review; facade aliasing is resolved and the nine earlier eastern images were restored byte-for-byte. The pre-fix aliased captures remain archived under [`before-mipmap-fix`](../evidence/building-streaming-2026-10-30/before-mipmap-fix/). The [validation record](../evidence/building-streaming-2026-10-30/validation.json) lists the final gates, preserved red runs, capture hashes and unchanged runtime inputs.

The isolated loader regression deliberately requests a missing temporary scene, consumes its failed native request token, creates the repaired fixture and retries successfully. Expected native missing-file diagnostics are muted only inside this fixture and normal diagnostics are restored in `finally`; assertion failures still report normally. Imported Blender `.001` proxy suffixes are matched to Godot's `_001` names, with one-to-one inventory checks across all 3,135 proxies.

Before building streaming, a normal eager-world launch measured 8,519.63 MiB peak and 8,053.16 MiB at the idle menu. The final normal-start measurement is 5,481.55 MiB peak / 5,479.90 MiB idle; method and limits are in [startup performance](STARTUP_PERFORMANCE.md). Detailed buildings now stream around the bus, while props, pedestrians, terrain masks and other world assets still load globally. The below-4 GiB peak goal remains unmet, and the 2–3 GiB steady-driving budget has not been demonstrated.
