# Building review — 12 September 2026

Reviewed actual Godot renders at Nathan Road, Haiphong Road, Chatham/Granville and the Jordan/western blocks, plus the Blender models and all generated building lots.

| Finding | Result |
| --- | --- |
| Exposed rear walls were blank from ground to roof. | Added framed windows, sills, varied closed curtains, air conditioners, drainpipes and a service door to all three models. |
| Side windows were flat rectangles, noticeably simpler than the fronts. | Added frames, mullions and projecting sills. |
| Every tower used the same bright wall colour. | Retained the generated tile texture with warm stone, muted jade and grey tints. The imported materials are checked so an export cannot silently discard the tint. |
| Roof parapets were missing their rear edge. | Completed the fourth side. |
| Building density might obstruct streets or consume the park. | The audit found zero overlapping lots, zero road intrusions and zero park intersections across 1,755 lots. Placement and density were retained. |

## Visual evidence

Six matching camera views are saved in `evidence/before-building-review/` and `evidence/building-review/`. These use the game renderer and normal lighting/fog at 1280 × 800. Captures explicitly draw a frame so an occluded desktop window does not stall the review.

The clearest comparison is `chatham-rear.png`; `nathan-front.png` and `haiphong-street.png` show the street façades, while `jordan-block.png` and `west-block.png` show the overall density. `granville-corner.png` checks close corner/shopfront details.

## Assets and repeatable checks

The revised editable source is `Art/buildings.blend`. `Tools/model_assets.py` exports the same three `Assets/Models/shop_*.glb` files through Blender MCP. Run it with `ONLY_BUILDINGS=True` to regenerate just the buildings:

```python
exec(compile(open('/Users/chanwaichan/workspace/antila/Tools/model_assets.py').read(), 'model_assets.py', 'exec'), {'ONLY_BUILDINGS': True})
```

The script creates an isolated scene and restores the previous scene afterward. Earlier models and script are retained in `Art/before-building-review/`; `Art/antila-assets.blend` retains the earlier complete asset set. No raster images were generated or altered in this pass.

```sh
./run.command --headless -- --building-check
./run.command --disable-vsync -- --building-review
./run.command --headless -- --self-test
```

The building check also runs at the start of the full self-test. It verifies lot separation, road/park clearance, one rendered instance per lot, single-mesh imports, model dimensions and retained tile textures/tints. The rear details fit within the existing 8.1 m half-depth; projecting front signs remain decorative overhead geometry outside the ground footprint.

Verified: C# build with zero warnings/errors; focused audit and six-view capture exited successfully. Buildings remain at 892 street-front instances plus 863 block interiors, 23.8–48.4 m high, in 535 spatial MultiMesh groups. Logs: `evidence/building-audit.log`, `evidence/building-capture.log` and `evidence/building-self-test.log`.

The full self-test also passed and exited successfully: 3,110 bus-sized road-clearance queries, all 14 junctions/48 signal approaches, audio and pause/camera/traffic regressions, a 366 m drive west via Haiphong and a 790 m drive east via Granville, then the complete 1.08 km service through three stops with 26 passengers and no route contacts.

## Remaining limits

Three tower shapes, repeated rooftop equipment and one shared cafe photo still make the city look repetitive. These are authored buildings on government road geometry, not reconstructions of individual Hong Kong properties. Unique landmarks, more building types, distinct shop interiors and a convincing distant skyline remain future art work.

The added detail raises the three source meshes from 4,796 / 6,932 / 7,316 triangles to 8,216 / 11,312 / 12,656, and from eight to nine material surfaces. Existing spatial batching is retained; no performance benchmark is claimed. Native keyboard/window checks were not repeated because macOS was locked; the actual renderer and in-engine checks remain available. The editor import completed but printed the previously observed Android SDK settings message at shutdown.
