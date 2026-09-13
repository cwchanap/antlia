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
