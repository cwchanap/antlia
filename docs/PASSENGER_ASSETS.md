# Scanned passengers

Prepared through Blender MCP on 12 September 2026 using free models from [Renderpeople](https://renderpeople.com/free-3d-people/). These are licensed scans, not imagegen outputs or original Antila character sculpts.

| Game asset | Source model | Source version |
| --- | --- | --- |
| `Assets/Models/passenger_mei.glb` | `rp_mei_posed_001` | 30k OBJ, supplied 2k diffuse texture |
| `Assets/Models/passenger_dennis.glb` | `rp_dennis_posed_004` | 30k OBJ, supplied 2k diffuse texture |
| `Assets/Models/passenger_family.glb` | `rp_fabienne_percy_posed_001` | 60k OBJ, supplied 2k diffuse texture |
| `Assets/Models/passenger_headphones.glb` | `rp_posed_00178_29` | Supplied GLB and base-color texture |

Each stop has four posed groups, including one parent-and-child group. They are representative waiting passengers; the service's existing 8/12/6 boarding counts remain unchanged. Models have no skeletal animation and disappear with their queue when boarding completes. They are rendered within 160 metres of the camera.

## Source and reproduction

- [Classic posed people ZIP](https://renderpeople.com/sample/free/renderpeople_free_posed_people_OBJ.zip): contains nested archives for Mei, Dennis, and Fabienne/Percy.
- [New posed person GLB ZIP](https://renderpeople.com/sample/free/rp_posed_00178_29_GLB.zip): contains the passenger wearing headphones.

Sources are kept under `Art/Passengers/<source model name>/`. The classic folders contain their 30k/60k OBJ and `tex/<source model name>_dif_2k.jpg`; the new model folder contains its GLB and supplied `tex/` directory. Run `Tools/import_passengers.py` through Blender MCP to rebuild the four exports. It creates an isolated `Antila_Passengers` scene and saves a packed, editable lineup to `Art/passengers.blend`.

Downloaded archive SHA-256: classic `42757bb8baef3ee31eb95cb0ade5ac93feaecb2d5b456628df57dc6a85ce4d1f`; new posed GLB `76071d1971f8df4d1a1585e56eb3f8254277874c7b2aa88a9b9d402d17c0fdff`.

The import converts centimetres to metres for the OBJ files and corrects the supplied new GLB's one-tenth scale. Mesh origins are centered horizontally and placed at the lowest foot point. Source UVs and diffuse textures are preserved. Materials use roughness 0.85; the supplied normal/specular maps are not used. Exports contain only the selected passenger, with its texture embedded. Assertions check human height, finite geometry/UVs and a bounded triangle count.

## License

© Renderpeople GmbH. The supplier's [terms and conditions](https://renderpeople.com/general-terms-and-conditions/) grant use of these free models for rendered imagery and computer/video games. They restrict redistribution or making the source models available as individual files. These assets are **not CC0** and are not part of the project's original generated art. Source files, the passenger Blender file and exported passenger assets are excluded from Git to avoid publishing them as a downloadable asset collection. Preserve these restrictions when distributing the game or sharing project source.

## Preview and checks

`evidence/passengers-before.png` preserves the earlier figures. `evidence/passengers.png` is the in-game close view of the replacement queue, with the bus body hidden for an unobstructed view. The existing full-route check now also verifies four model groups per stop and that boarded queues disappear.

The four exports were checked for one mesh, one embedded texture, finite source UVs, and grounded feet. Heights are 1.697 m (Mei), 1.871 m (Dennis), 1.714 m (family) and 1.725 m (headphones). They contain 30,004 / 30,039 / 59,961 / 50,033 triangles respectively. The final C# build completed with zero warnings and errors, and the rendered queue was visually inspected in Godot.

The full 1.08 km driving regression passed all three stops, loaded four passenger groups per stop, removed all boarded queues, and finished with 26 passengers and no route contacts. The final test and six-view capture exited without warnings or errors.

## Runtime texture storage

The four extracted JPEG `.import` sidecars are versioned separately from the licensed model/image files. Dennis, the family and the headphones passenger use desktop VRAM compression (BC1/DXT1 on the tested GL Compatibility renderer). Mei stays lossless: the actual Godot importer produced visible blue/purple skin artefacts at both normal stop distance and close range. This exception is pinned in her sidecar with automatic 3D compression detection disabled, so an editor preview cannot switch her back to BC1.

| Passenger | Resolution | Mip levels | Tested resident texture payload |
| --- | --- | ---: | ---: |
| Mei | 2048 × 2048 | 12 | 16.00 MiB, RGB8 |
| Dennis | 2048 × 2048 | 12 | 2.67 MiB, BC1 |
| Family | 2048 × 2048 | 12 | 2.67 MiB, BC1 |
| Headphones | 4096 × 4096 | 13 | 10.67 MiB, BC1 |

The actual bound textures total **33,554,471 bytes (32.00 MiB)**, down from **117,440,508 bytes (112.00 MiB)**: **83,886,037 bytes (80.00 MiB) less texture data**. The source JPEGs, embedded GLB textures, UVs, geometry, resolutions and complete mip chains retain their prior bytes/contracts. Only import settings are committed; the license exclusions for model/image/Blender files remain in place.

After rebuilding the licensed GLBs through Blender MCP, run the usual Godot import step. The extracted texture names retain their checked-in settings. Verification rebuilt all four passenger scene caches and checked that the four sidecar hashes survived unchanged. Other platforms can select different GPU formats; the table above is the tested macOS GL result.

Evidence is local under `evidence/passenger-compression-2026-11-16/`. Sixteen native comparison views cover front/back bodies at 2.3 m and faces/clothing at 1.05 m. The final comparisons use the actual imported textures, not just an in-memory compression prototype. Minor fine-detail differences remain on the compressed artwork; Mei’s restored RGB bodies are pixel-identical in all four views. Source checks verify one allocation per texture, unchanged dimensions/full mip payloads, physically driven H3, scene reload, footpath/collision details and 72 rendered terrain-boundary probes.

These are offscreen rendering and functional checks. The user selected offscreen checks after the live-window attempt became non-drawable; that attempted timing/physical-footprint run is excluded. No new live RAM/FPS, cross-GPU or manual-driving result is claimed. See the companion [performance notes](STARTUP_PERFORMANCE.md#passenger-texture-compression).

The standalone macOS debug export also passed the exact four-allocation budget and the filtered H3 offscreen route (four stops / 33 passengers). Its deep/strict local signature check passed after runtime verification. Temporary export settings and profiling callbacks are removed; the JPEG/GLB source hashes and unrelated import settings are preserved.
