# Eastern Kowloon expansion — 21 October 2026

The map now extends through Hung Hom, Whampoa, To Kwa Wan and Kowloon City. **P while stopped** starts a 6.111 km exploration drive from the existing Chatham Road approach to Nga Tsin Long Road at Carpenter Road. It follows Chatham Road North, Wuhu Street, Tak Man Street, Hung Hom Road, Tak Hong/Tak Ting/Tak On streets, Chi Kiang Street, To Kwa Wan Road, Sung Wong Toi Road, Ma Tau Chung Road and Kowloon City's street grid. Source segment IDs are explicit in `Tools/import_tunnel.py`.

This adds 1,507 TD road sections (6,671 total), a thirteenth exploration drive, 6,840 derived building parts, sourced eastern shoreline, street lamps, trees, pedestrians and kiosks. The earlier 5,164 road records, twelve drives and both tunnel profiles are exactly unchanged. The world bounds now span 17.11 × 13.43 km. New regional selection bounds are X 550–3150 m, Z −4700 to −100 m, overlapping the earlier map to connect its streets.

The [eastern open-space follow-up](EAST_KOWLOON_OPEN_SPACES.md) fills nine reviewed park/waterfront gaps using freshly verified iB1000 boundaries and sports outlines, with authored paths, planting and seating. It preserves the expansion's roads, buildings and services.

## Sources and scale

- [Transport Department Road Network](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2): official CENTERLINE.kmz, HK1980 geographic EPSG:4611 converted to WGS84. Stable ROUTE_ID values preserve older road snapshots. 5,161 shared sections match within 2.5 cm; three revised earlier sections remain pinned. The 6.119 km raw itinerary becomes 6.111 km with the existing 4 m sampling. Every sampled centreline point stays on its source line; corner chord deviation is under 0.90 m on this drive.
- [Lands Department iB1000](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html): 41 GML sheets, 576 existing shoreline, seawall/high-water and pier fragments. EPSG:2326 northing/easting is converted to WGS84. The regional land polygon covers 8.664 km² and has 7.202 km of shoreline. Straight repairs are recorded in the coast JSON; the longest is 41.69 m. Inland map cuts are authored. The retained TST apron is unchanged.
- [Lands Department Building dataset](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1637211194312_35158): 6,559 source parts, yielding 6,840 clipped upper-envelope parts from 5,969 retained IDs, covering 2.159 km². 335 source parts need the established storey-height fallback. Earlier regions are excluded to prevent duplicate buildings; the eight Kowloon extracts share base/height reconciliation. All changed layouts have matching rebuilt Blender assets.

Source files retain query bounds, retrieval timestamps and hashes. © HKSAR Government / Transport Department / Lands Department; [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC), [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions). No Google imagery is used.

The established projection uses approximately one metre per unit, +X east and −Z north. Flat terrain, 12 m surface-road widths, paving, seawall height, greenery, people and facade textures are authored. Turn restrictions and full traffic rules are not inferred. This is an exploration expansion; it does not add a scheduled bus service or a surveyed reconstruction. Kai Tak geometry inside the selection is partial; the rest is outside this release.

## Assets and earlier regions

Blender MCP exports `hung-hom-buildings.glb`, `to-kwa-wan-buildings.glb` and `kowloon-city-buildings.glb`, with 477 matching visual/collision chunks. Each is below 100 MB and reuses the existing generated facade/shopfront textures. `cross-harbour.glb` contains the joined ground, water and boundary walls. Modeling restores the user's original Blender scene. The new vertical seawall probes exposed inward-facing faces in the shared wall mesh; the generator now builds outward-facing closed walls, including their top surface. The failing baseline is saved before the fix. All 492 existing tunnel/deck mesh streams remain identical.

Regenerating the shared building pipeline also updates clipped components in earlier regions; their source footprints remain from their original extracts. No earlier road record or exploration drive is changed. The new `TD_105213` Hong Chong Road branch makes H3's old 435 m waiting area part of the carriageway, so its fictional first stop moves 90 m along the same alignment to the survey-confirmed 525 m shelter site. All other stops and passenger totals remain the same. Current regional part counts:

| Region | Parts |
|---|---:|
| Original Kowloon | 1,765 |
| Yau Ma Tei / Mong Kok | 5,109 |
| Western Kowloon / Sham Shui Po | 6,094 |
| Cheung Sha Wan / Lai Chi Kok | 2,798 |
| Lai King / Kwai Chung | 3,425 |
| Tsuen Wan | 4,997 |
| Ting Kau / Sham Tseng | 2,134 |
| Hong Kong Island | 5,097 |
| Eastern Kowloon | 6,840 |

## Regeneration

The October 21 snapshot used `Tools/import_shoreline.py --east-kowloon --download` and imported its HK1980 archive with `Tools/import_tunnel.py /path/to/CENTERLINE.kmz --hk1980`. The current map uses the November WGS84 archive. [Current regeneration workflow](KOWLOON_CITY_DISTRICT_REVIEW.md#repeat-the-audit)

## Verification

Evidence is under `evidence/east-kowloon-expansion-2026-10-21/`. The baseline contains source/code copies and SHA-256 values from before this work. `Tools/check_east_kowloon.py` checks source sampling, direction, connections, shore, water, overlapping regions and building clearance. `--east-kowloon-check` physically drives the new itinerary and checks the P key with map/pause/completion/moving guards, lane support and seawall collision. `--east-kowloon-review` records seven native district/stop views plus the map. `--self-test` covers all existing routes; `--restart-check` includes the eastern drive in eight reloads; add `--restart-capture` to record the final eastern views after those reloads.

Source, importer, model preservation and shared-height checks pass. The full headless suite exits 0 with `ANTILA_SELF_TEST_OK`: all thirteen exploration drives, seven ramp/flyover drives, both side-street turns, 122,985 full bus-envelope queries and H1/H2/H3 passenger services pass. The eastern itinerary physically covers 6,007 m without contacts. H1 serves 26 passengers at three stops, H2 serves 60 at eight stops, and H3 serves 33 at four stops, with no contacts or red-light crossings. The H3 stop correction passes the formerly failing stop-table and service checks. Build: 0 warnings / 0 errors.

The native capture passes the P key and four guards, 678 lane-support probes and 25 seawall probes. All seven district/stop views and the map have been inspected. The native restart/render check exits 0 after eight reloads, including the eastern drive and a completed service. All nine world states restore H1 with 5,864 building meshes and 2,932 collision shapes and no engine errors. The native playground shader check passes 72 inside/outside boundary probes, the centre and asphalt priority. The final credit-label build passes with 0 warnings / 0 errors. A fresh native run exits 0 and records all eight views, including the relocated Hong Chong Road shelter; every view was inspected. The menu and driving HUD share the updated data credit. The full driving/reload suite precedes this display-only cleanup; final build and native captures include it.


Road KMZ SHA-256: `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`.

Eastern building extract SHA-256: `4556e146f1c9492dab4dd2f4fc0d91ce984e6e2ce102712f38adc7851d07c876`.

Shoreline source SHA-256: `aecd6b3db767a36d5af39b0b777f79f0a3a65c6d41b60a0b7871e668b601ed36`.

[View the screenshot gallery](../evidence/east-kowloon-expansion-2026-10-21/index.html). Final markers, counts and image hashes are collected in `evidence/east-kowloon-expansion-2026-10-21/verification.json`.

## Government-data review repairs — 21 October 2026

The review found two missing roundabout rings and a remaining fence around the original district. The importer now explicitly retains eight unnamed TD ground-level sections: Hereford / Renfrew `107211 → 107576 → 107598 → 107575 → 107601`, and Ho Tung / Oxford `107564 → 107580 → 107235`. Each list closes in the source's one-way digitised direction, with named streets connected at its nodes. Their raw source length is 148.613 m. Other unnamed access links remain excluded pending clearance/access assessment. The road dataset now has 6,671 sections; the thirteen exploration itineraries are unchanged.

The original district rectangle no longer creates an internal collision fence. The harbour asset encloses the joined mainland's actual edge, including the retained authored TST apron, and keeps the existing source seawalls. This removes the internal seam while protecting the true outer edge. The physical barrier regression now drives into the eastern outer boundary instead of requiring the obsolete fence in Hung Hom.

`Tools/check_east_kowloon.py` checks both directed rings, their approach connections, source sampling and building clearance, plus ground-perimeter wall coverage. The HUD regression covers all thirteen unnamed links, including the eight restored sections. `CheckEastMapFixes` checks asphalt and ground support across both rings, an unobstructed former fence site and retained outer-wall collision. It runs with the eastern check and full self-test. Failing baselines and subsequent verification are recorded under `evidence/east-kowloon-review-fixes-2026-10-21/`; the original review remains under `evidence/east-kowloon-expansion-2026-10-21/gov-review/`.

The repair build has 0 warnings / 0 errors. The fresh full suite reaches `ANTILA_SELF_TEST_OK`: all twenty exploration/ramp drives, H1/H2/H3 services, both side-street turns and 123,012 full bus-envelope queries pass. The new check passes 123 roundabout asphalt/support probes, the clear former fence site and both real perimeter-wall sites. The final physical barrier test contacts `KowloonBoundary` at the true eastern edge. All 6,663 prior road/source records, thirteen exploration itineraries, two tunnel profiles, building layouts, land/water/coast data, 492 prior tunnel/deck mesh streams and 43 other GLB assets are preserved. The eight-reload sweep above was not repeated for these repairs.

The native capture exits 0 with both new map-fix markers and no engine errors. All three matched views were inspected: the two road rings are continuous and the old orange interior fence is absent. An independent read-only review found no actionable issues. [Before/after gallery](../evidence/east-kowloon-review-fixes-2026-10-21/index.html), [verification record](../evidence/east-kowloon-review-fixes-2026-10-21/verification.json), [independent review](../evidence/east-kowloon-review-fixes-2026-10-21/independent-review.md).
