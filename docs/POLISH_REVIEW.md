# Road and streetscape polish

The review used actual Godot renders at road level and above the Salisbury Road, Chatham Road and Jordan blocks. Before images are retained in `evidence/before-polish/`.

| Finding | Correction |
| --- | --- |
| Pavement, asphalt and ground broke into triangles at distance because stacked surfaces competed for depth. | One terrain shader now blends these surfaces from a generated road/pavement/park mask. There are no overlapping road planes. |
| Imported segments restarted markings; parallel and crossing sections drew tangled yellow lines. | Join unambiguous same-name endpoints, keep forks, allow parallel lane guides, and suppress paint at crossings and covered road edges. Paint uses a few shared meshes. |
| Old Nathan Road caps blocked streets inside the expanded map. | Remove both caps, extend the physical road to its extracted endpoints, retain barriers only at the outer map boundary. |
| Isolated, vertically stretched buildings lined otherwise empty blocks. | Use shared footprint checks for frontage and infill, moderate height variation, connected pavement pads and street-facing signs. There are 892 frontage and 863 infill buildings. |
| Increased density could multiply rendering cost. | Reuse the existing Blender meshes through 535 spatial MultiMesh batches. No new asset dependency was added. |
| Park planting looked like a grid, with floating sphere hills behind the district. | Scatter trees around paths and remove the sphere backdrop. |

The 231 H1 samples, three stops and all 437 source side-street sections are unchanged. Runtime joining reduces the latter to 260 polylines. This remains an authored streetscape with approximate road widths; there is no new traffic-light or one-way routing simulation.

## Visual evidence

| Before | After |
| --- | --- |
| ![Salisbury before](../evidence/before-polish/junction-salisbury.png) | ![Salisbury after](../evidence/junction-salisbury.png) |
| ![Block density before](../evidence/before-polish/density-block.png) | ![Block density after](../evidence/density-block.png) |
| ![Haiphong before](../evidence/before-polish/west-street.png) | ![Haiphong after](../evidence/west-street.png) |

## Verification

- C# build: zero warnings and errors.
- Terrain-mask placement and crossing/open-street marking checks passed.
- 3,110 bus-sized physics queries found no static road obstruction, including both former Nathan Road caps; ambient taxis were excluded from this static-clearance audit.
- Physically drove 366 m west and 790 m east with turns from Nathan Road and no contacts; completed H1 with all three stops and 26 passengers. Results are in `evidence/self-test.log`.
- Rendered views use the normal game renderer; aerial review captures disable fog and move the near clip plane for legibility. Capture FPS is a local sample, not a benchmark.

The normal launcher rebuilt successfully and left the polished game running. Native window inspection could not proceed because the computer-use tool reported a locked macOS session. Rendered evidence and in-engine checks completed successfully.
