# Road polish — 12–13 September 2026

- Corrected reversed paint triangles. White lines, crossing studs and yellow bay/junction markings now receive light from above; the mesh check verifies winding.
- Added lane divisions and mesh arrows following left-hand traffic. Connected parallel segments of the same road now share one lane layout: for example, the 30.1 m Chatham section has six lanes around a single centre divide. Separate road branches remain separate.
- Centre divides follow connected samples around bends. Full marking footprints are checked against the asphalt at tapers and forks. Crossings and signal approaches use the combined carriageway width; every approach lane is checked for the correct signal. Crossing studs are trimmed at the kerbs. The corrected crossing edges support 82 pavement landings, up from 73.
- Lane guides and arrows stop before crossing studs, stop lines and bus bays. Three yellow boxes sit inside the Nathan / Haiphong, Kimberley and Austin junctions.
- Moved the authored Kowloon Park stop from 520 m to 535 m: its previous bay crossed the Granville pedestrian crossing. Shelter, queue, boarding tiles, furniture and service marker follow the stop data. All three bays have ground lettering.
- Added fractional coverage at road/path mask edges at the existing three pixels per metre. Government centrelines and driving surfaces retain their geometry.

Existing generated textures are reused; paint remains batched by colour. Yellow boxes and arrows are visual markings, with no new turning restrictions or box-junction penalties. Locations and lane counts remain authored approximations. Visual reference: [HK Transport Department road markings](https://www.td.gov.hk/en/road_safety/road_users_code/index/chapter_8_the_language_of_the_road/road_markings_giving_orders_/index_t.html). Mesh convention: [Godot SurfaceTool](https://docs.godotengine.org/en/4.4/classes/class_surfacetool.html).

## Reproduce

```sh
./run.command --headless -- --road-check
./run.command --headless -- --self-test
./run.command --disable-vsync -- --road-review
```

The focused check verifies paint is on asphalt and clear of crossings/bays, arrow direction and overlap, bay clearance, fractional road-edge coverage and consistent carriageway geometry in both travel directions. The full self-test also exercises scenery, pedestrians, audio, signals, road collision clearance and actual driving.

Original baseline/final renders are in `evidence/before-road-review/` and `evidence/road-review/`. The carriageway follow-up baseline is in `evidence/before-carriageway-review/`; its source backup is in `Art/before-carriageway-polish/`. The road capture now saves eight views, including a Chatham driver view and overhead crossing view.

| Before | After |
| --- | --- |
| ![Haiphong before](../evidence/before-road-review/haiphong-junction.png) | ![Haiphong after](../evidence/road-review/haiphong-junction.png) |
| ![Bus bay before](../evidence/before-road-review/park-bus-bay.png) | ![Bus bay after](../evidence/road-review/park-bus-bay.png) |
| ![Chatham before](../evidence/before-carriageway-review/chatham-junction.png) | ![Chatham after](../evidence/road-review/chatham-junction.png) |

Carriageway follow-up verification: build passed with zero warnings/errors. The final paint check passed 4,967 marking checks, 379 arrows, 1,910 crossing studs inside the kerbs, stop-line placement and all three bay clearances (`evidence/carriageway-edges.log`). Eight final rendered views were inspected (`evidence/carriageway-review.log`). Scenery, audio and all 48 signal approaches passed, followed by 3,110 bus-sized road queries, both side-street drives and the complete 1.08 km service with three stops, 26 passengers and no route contacts (`evidence/carriageway-self-test.log`). The final kerb trim changes only crossing paint and was checked separately after the full drive. These verification processes exited zero without shutdown warnings.

## Extension continuity — 20 September 2026

The harbour's separate flat asphalt mesh produced a lighter 12 m strip over the original wider roads. It is now hidden and the extension uses the same terrain material, combining a separate 2 px/m road/pavement mask with the original district mask. A small paint shader suppresses extension centre lines wherever the original district already has asphalt. This keeps one visible flat surface and carries paving and kerb edging through the district boundary. The source road paths, authored widths and collision ground remain unchanged. [Before/after area review](AREA_REVIEW.md#implementation-follow-up).
