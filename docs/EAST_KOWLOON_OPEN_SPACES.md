# Kowloon and western New Territories open spaces

## Tsim Sha Tsui, Jordan, Yau Ma Tei and Tai Kok Tsui

| Area | Sites |
| --- | --- |
| Tsim Sha Tsui | Signal Hill Garden, Salisbury Garden, and the Tsim Sha Tsui Promenade |
| Jordan | King George V Memorial Park |
| Yau Ma Tei | King's Park Rest Garden, King's Park Recreation Ground, and Man Cheong Street Park |
| Tai Kok Tsui | Hoi Fai Road Park, Hoi Fai Road Promenade and Playable Space, Lok Kwan Street Park, and Sycamore Playground |

The four-district refresh provided **39 sites, 132 sports outlines, 94 fitted courts, 3,629 fixtures and 100,289 paving triangles**. Its 52 official map sheets supply 86 Site and 147 sports fragments.

The iB1000 Site and BuiltStructurePolygon features provide the boundaries and sports outlines. Footpaths, entrances, seating and planting are authored for the flat game terrain and checked for access from existing public paving. Hoi Fai Road's three sites are distinct from Hoi Fan Road Park in the earlier fill. The football pitches at King George V Memorial Park and Sycamore Playground use hard surfaces, following the venue listings. [King George V venue listing](https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?ftid=56), [Sycamore venue listing](https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?did=17&fcid=8&ftid=11).

Transport Department centrelines add 23 Wylie Road sections and three King's Park Rise sections. The northern building footprints were reclipped to their 3.5 m carriageway clearance. The engine checks both the signed Wylie Road to King's Park Rise drive and the established Jordan to Mong Kok drive. The 14 exploration itineraries and H1–H3 service data retain their original paths.

The Tsim Sha Tsui ground and water meshes use 1.14 km of joined iB1000 Site and SWA seawall frontage. The cut returns 38.40 hectares of the former apron to the harbour, before 0.41 hectares of sourced public ground are restored around the two waterfront sites. The Hung Hom Harbourfront approach is clipped to the ground edge and retains its connection to street pavement. The shoreline source and its sheet hashes are in `Data/tst-shoreline-source.geojson`. Run `Tools/check_tst_shoreline.py` with the geodata environment to verify the land, coast and road clearance.

The Centenary Garden drainage works are marked in game at the iB1000 work-in-progress annotation. The drainage project is scheduled to finish in mid-2027. [Drainage Services Department project 4175CD](https://www.dsd.gov.hk/EN/Our_Projects/All_Projects/4175CD.html).

The offline check reproduced the layout exactly from the 52 source sheets and rejected 41 invalid refresh cases without overwriting either output. The game passed 159 path, entrance and ground-support probes, 132 sports-surface probes, fixture clearance for all 3,629 fixtures, and 94 recreation collider checks. The terrain-mask check matched all three baked masks. The King’s Park drive and the existing Jordan–Yau Ma Tei–Mong Kok drive passed without contacts during integration. Rebuilding the paths also repositioned benches at ten earlier sites.

## Southwest Kowloon waterfront

The waterfront correction follows the Lands Department harbour outlines between West Kowloon Art Park and Tsim Sha Tsui. Surveyed ferry decks and buildings retain support. Ground now covers the charted public promenade south of the Cultural Centre site. The museum seawall follows the corrected water edge east of the site. The terrain paving mask uses the surveyed footprints of piers and floating landings. [Tsim Sha Tsui GeoPDF](https://www.landsd.gov.hk/doc/en/mapping/ehkg/MapPages/GeoPDF/KN12_TsimShaTsui.pdf) · [West Kowloon GeoPDF](https://www.landsd.gov.hk/doc/en/mapping/ehkg/MapPages/GeoPDF/KN13_WestKowloon.pdf)

The Cultural Centre has a paved piazza on its surveyed site and uses at-grade pedestrian detail for its street and promenade connections. Wonderland uses its surveyed site outline to reserve open event ground. The two sites bring the layout to 41. Local clearance changes update paving and bench placement at Signal Hill Garden, Salisbury Garden and the Tsim Sha Tsui Promenade. [Cultural Centre site map](https://www.lcsd.gov.hk/en/hkcc/common/b5/hiring/files/HKCC%20Site%20Map%20%28Jun%202024%29.pdf) · [West Kowloon Art Park access guide](https://webmedia.westkowloon.hk/documents/Art-Park-Access-Guide-202601-EN-tagged.pdf)

## West Kowloon fill — 17 November 2026

The earlier West Kowloon fill added **West Kowloon Art Park and the Waterfront Promenade**, retaining **106,109.57 m²** of government Site boundaries. It contains **27 sites, 120 sports outlines across 135 fragments, 88 unchanged sport fittings, 3,302 fixtures and 86,722 paving triangles**, with 121 interior path/access probes. The earlier 25-site source features, garden/path/access/sample arrays, all 3,068 fixtures, 120 surfaces, 88 fittings and 81,836 paving triangles remain exact.

| Site | Source ID | Source area (m²) | Paving (m²) | Trees | Benches |
| --- | --- | ---: | ---: | ---: | ---: |
| West Kowloon Art Park | `1910053970` | 99,677.28 | 14,189.23 | 106 | 113 |
| West Kowloon Waterfront Promenade | `1910053968` | 6,432.29 | 4,790.63 | 1 | 14 |

Art Park retains three Site patches: two on `11-NW-23D` and one on `11-SW-3B`. The promenade retains one patch on each sheet. Official map annotations identify Art Park and Waterfront Promenade; the [WestK Art Park access guide](https://webmedia.westkowloon.hk/documents/Access-Guide-202501_Art%20Park_EN_FINAL_tagged.pdf) provides a venue cross-check. All 194 selected source features comprise 59 Site patches and the unchanged 135 sports patches. The complete 230-row official index and 38-sheet hash/provenance manifest are bundled in `Data/kowloon-open-spaces-index.json` and `Data/kowloon-open-spaces-tile-manifest.json`; retrieval was 17 November 2026 UTC. Selected sheet revisions span 29 July–21 October 2026. New source feature dates are 3 September 2023 for Art Park and 13 January 2026 for the promenade.

The promenade uses a 1.5 m path inset to retain its narrow waterfront strip. It connects through Art Park paths; the direct road approach intersects building clearance. Where paths already touch public paving, the entrance generator starts inside the retained path before applying the existing 250 m, land, building, carriageway and sports-clearance checks. A focused regression exercises that zero-distance case. The source checker retains the interior promenade probe at `(-1600, -415.5)` and rejects missing, duplicate or wrongly attributed Art Park patches while another same-ID patch remains on the same sheet.

Paving, paths, planting and seating are authored approximations, with existing flat ground and shoreline. The new fill places 107 trees and 127 benches using existing assets; its reservations displace three generic roadside trees, leaving 1,268 in the separate harbour-scenery inventory. There are no new sports fittings, so the Blender recreation asset is unchanged. The combined terrain bake refreshes the harbour PNG, RG8 resource and source-linked sparse metadata; it preserves the existing recreation bounds and sports data.

Regenerate and check with:

```sh
.venv-geodata/bin/python Tools/import_east_open_spaces.py --extract CACHE_DIR Data/kowloon-open-spaces-tile-manifest.json
.venv-geodata/bin/python Tools/check_east_open_spaces.py CACHE_DIR Data/kowloon-open-spaces-tile-manifest.json PRESERVATION_BASELINE_DIR
./run.command --headless -- --bake-terrain
./run.command --headless -- --terrain-mask-check
./run.command --headless --fixed-fps 60 -- --self-test
```

Run native `--harbour-rg8-check` and `--sparse-recreation-check` for texture filtering. The preservation baseline for this fill is the prior 25-site `Data/` snapshot. Evidence, matched overview captures and focused Art Park/promenade views are retained in `evidence/west-kowloon-open-spaces-2026-11-17/`. Detailed internal landscaping, current venue access, scene-reload stress and a new performance benchmark are outside this fill.

Verification on 17 November: the build passed with **0 warnings / 0 errors**. The source checker passed deterministic regeneration and **30 rejected-input preservation cases**, including the same-ID/same-sheet Art Park patch regression. The full engine suite exited 0: **133,749 bus-envelope queries, 25 physical exploration/approach drives, H1/H2/H3, all 15 scheduled stops and 119 passengers**, plus the original 1.08 km driving/boarding regression. West Kowloon’s drive covered 6,099 m without contacts. Native checks passed all **121 paving/connectivity/support probes, 120 sports probes, 861 infield probes, 3,302 fixture clearances and 88 fitting colliders**; six final views were inspected. The rebuilt RG8 paving resource matched its RGB source over **186,122,240 GPU pixels in 710 windows**, with no differences at 1/255. The recreation PNG, sparse binary resources, original surface mask and sports GLB remain byte-identical; the full sparse source/mip round-trip passed, and native sparse filtering was not repeated. [Before/after gallery](../evidence/west-kowloon-open-spaces-2026-11-17/index.html), [verification record](../evidence/west-kowloon-open-spaces-2026-11-17/verification.json).

## Sham Shui Po, Cornwall Street Park and Kowloon Tong — 18 November 2026

The final 59-site recreation inventory adds five larger Sham Shui Po district sites, six Nam Cheong Street sitting-out areas, Cornwall Street Park and six Kowloon Tong sites to the previous 41-site inventory. The 57 source-bounded sites plus two supplemental southwest waterfront spaces use **284 iB1000 features**: 115 Site patches and 169 sports-outline sheet fragments. The combined layout contains **152 source sports outlines, 109 intact sport fittings, 3,997 fixtures and 115,264 paving triangles**.

| Site | iB1000 Site ID | Site sheets |
| --- | --- | --- |
| Tung Chau Street Park | `1503005112` | `11-NW-13D`, `11-NW-14C` |
| Maple Street Playground | `1503005184` | `11-NW-14A`, `11-NW-14C` |
| Sham Shui Po Park | `1503005071` | `11-NW-13B` |
| Sham Shui Po Park Stage 2 | `1503005077` | `11-NW-13B` |
| Tai Hang Tung Recreation Ground | `1503005450` | `11-NW-14B`, `11-NW-14D` |
| Nam Cheong Street Sitting-out Areas 1–4 | `1503005180`, `1503005170`, `1503005157`, `1503005144` | `11-NW-14A` |
| Nam Cheong Street Sitting-out Areas 5–6 | `1503005135`, `1503005123` | `11-NW-14C` |
| Cornwall Street Park | `1503005508` | `11-NW-9B`, `11-NW-9D` (two patches), `11-NW-10C` |
| To Yuen Street Playground | `1503005539` | `11-NW-9D` (two patches), `11-NW-10C` |
| Kent Road Garden | `1503005553` | `11-NW-10A`, `11-NW-10C` |
| Kam Shing Road Recreation Ground | `1503005688` | `11-NW-10A`, `11-NW-10B` |
| Cornwall Street Children's Playground | `1503005627` | `11-NW-10A` |
| Cornwall Street/Ede Road Garden | `1503005605` | `11-NW-10A` |
| Dorset Crescent Rest Garden | `1502005648` | `11-NW-10A`, `11-NW-10C` |

The Kowloon Tong refresh preserves the 11 exact Site patches across those six additions and adds the three basketball courts `1500001910`, `1500001941` and `1500001955` from sheets `11-NW-10C`, `11-NW-10C` and `11-NW-10A`, respectively. Kent Road Garden's nonrectangular `1500001941` surface remains unchanged; its fitted court uses a 0.5 m inscribed rectangle measuring 14.019 × 25.379 m. Cornwall Street/Ede Road Garden uses a compact walkable plaza treatment, while Dorset Crescent Rest Garden fits one bench and one planter around its access path. Cornwall Street Park's paths, access and furniture are regenerated against the restored squash and tennis centre's current building clearance.

The two Tung Chau Street Park football pitches and Maple Street Playground pitch use hard-court styling, following the current [LCSD Tung Chau facility listing](https://www.lcsd.gov.hk/en/parks/tcsp/facilities/outdoor.html) and [Maple Street refurbishment record](https://www.lcsd.gov.hk/en/common/images/en/doc/2020/HAB366E.pdf). Tai Hang Tung retains two surveyed gateball outlines as simple courts and its three football pitches as grass fields, checked against the [official recreation-ground plan](https://www.lcsd.gov.hk/ls/tender/en/list/forms/LCLSQLRKSSPTHTRG202001_EN.pdf). Sports footprints and categories remain tied to the government outlines.

The six narrow Nam Cheong Street areas use their safe remaining site ground as paved sitting-out space, each with an authored corner bench and a tested connector to existing public paving. Bench circles stay at least 3 m (2.7 m for the two smaller benches) from the path probes and clear the entrance corridor. Sham Shui Po Park Stage 2 uses a checked authored 86.7 m access route to Lai Chi Kok Road after the automatically nearest connector failed building clearance. Cornwall Street Park retains all four Site patches across sheets 9B, 9D and 10C, giving 23,984.65 m² of source ground; its generated paths connect to existing public paving without a custom road target. Paths, entrances, paving, benches, planting and finish are authored approximations rather than surveyed internal park layouts.

The Tai Hang Tung gateball courts use small gates and centre poles sized from the published equipment dimensions. [World Gateball Union rules](https://gateball.or.jp/wgu/play/pdf/play05_02.pdf)

The source checker validates the exact Site and sports `(ID, sheet)` fragments, regenerated path and access geometry, a probe for every paved component and fixtures on all six sitting-out areas. The interior paving-probe clearance is 1.1 m, and the compact entrances use a 0.75 m step inside each narrow site. Tung Chau fixture placement treats building `214665`'s outer footprint as solid, including its courtyard ring, to match runtime clearance. Existing sports outlines and site boundaries retain their surveyed geometry. Rebuilding the paths repositioned benches at 16 earlier sites.

The final in-game park and path checks passed on the 59-site layout, with 109 fitted court colliders and 3,997 clear fixtures. The focused refresh check reproduced the staged JSON byte-for-byte and rejected a detached paving component after its connectivity probe was removed.

## 28 October source snapshot

At the 28 October snapshot, the western fill extended the eastern Kowloon and [Wong Tai Sin map](WONG_TAI_SIN_EXPANSION.md) with nine reviewed sites. That snapshot contained **25 sites, 120 source sports outlines across 135 sheet fragments, 120 rendered sport surfaces, 88 intact court/field fittings, 3,068 authored fixtures and 81,836 paving triangles**. Its 116 path/access samples cover all retained paving components. The previous 16-site snapshot had 71 outlines across 81 fragments, 50 fittings, 1,505 fixtures and 44,518 paving triangles; those records remain exact in the integrated output.

The 25 sites are the original nine eastern Kowloon parks and waterfront spaces; Morse Park, Junction Road Park, Choi Hung Road Playground, Lion Rock Park, Diamond Hill Water Feature Park, Ma Chai Hang Recreation Ground and Fung Tak Park; and Hoi Fan Road Park, Central Kwai Chung Park, Shek Kip Mei Park, Lai Chi Kok Park, Nam Cheong Park, Shing Mun Valley Park, Kwai Chung Park, Tsuen Wan Park and Tsuen Wan Riviera Park. Road, building and scheduled-service geometry remains the Task 1 result.

## Sources and authored details

Site boundaries and sports outlines come from the Lands Department's [iB1000](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html) GML archives, reached through the [CSDI sheet index](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0). The complete official index response covers WGS84 bounds **114.100–114.204° E, 22.295–22.380° N** and contains 230 rows. It was retrieved `2026-10-29T03:27:54.240973+00:00` UTC (28 October in Vancouver); its SHA-256 is `cb6b0f3a75b5f6fa4f32c09f89539ca552f95f29804520abb5245ab062d92adf`. The selection contains 36 complete sheets. Their URLs, revision dates, retrieval times and archive SHA-256 values are recorded in `Data/east-kowloon-open-spaces-source.geojson` and `evidence/western-map-fixes-2026-10-28/combined-tile-manifest.json`. The source bundle was retrieved `2026-10-29T03:30:12.144590+00:00` UTC. Source feature `LASTUPDATEDATE` values range from **2023-09-03 to 2026-08-06** for both Site and sports features; selected sheet revision dates range from 29 July to 10 October 2026. The raw source contains **54 Site fragments and 135 sport fragments** (189 features total). Tsuen Wan Park retains two separate Site patches from `6-SE-25B`; five sports outlines also retain patches across multiple sheets: `1500004928`, `1810018589`, `1810061752`, `1910085685` and `1910085686`. The complete per-feature revision tables and all archive hashes remain in the source GeoJSON.

GML coordinates use EPSG:2326 northing/easting/height and are converted to WGS84 with the source axis order recorded in metadata. The local projection uses origin 114.17232° E, 22.295° N, +X east and −Z north, approximately one metre per unit. Layout clearance hashes cover all nine current building layouts, the current road network and five coastal land masks: east Kowloon, west Kowloon, Lai Chi Kok, Kwai Chung and Tsuen Wan. Reusable source archives remain external to the runtime; the offline source/layout files contain the selected polygons and provenance.

Paths, entrance connections, planting and benches are authored inside usable space. Separated path loops gain 3.6 m wide connections only where the complete corridor fits clear garden ground; paths can also connect through existing public pavement. Sub-square-metre paving slivers are omitted. Connections beyond site edges stay on existing terrain and clear of carriageways and buildings; the Hung Hom Harbourfront connection is approximately 165 m long. Goals, nets, hoops and markings use the existing Blender recreation model, fitted only where the retained sports polygon supports an intact rectangle. Penalty markings adapt to narrow fitting widths, and the model builder checks every paint vertex against its fitted source rectangle. Facades, flat terrain and vegetation species remain approximations. The retained Yamen/theatre/pavilion massing is preserved; detailed heritage reconstruction is outside this scenery fill.

Irregular source outlines retain their ground surface without forcing rectangular markings outside their boundaries. The 49 new western sports IDs add 54 sheet fragments to the previous 71 IDs and 81 fragments. Fitting records exist only for source polygons that safely contain an intact authored rectangle; the Blender asset is regenerated from those records through the existing model workflow.

LCSD venue descriptions independently confirm Hoi Sham's four tennis courts, two football pitches and basketball court; Kowloon Tsai's mixture of turf and hard-surface grounds; and the parks' landscaping/recreation uses. Exact links and material evidence are recorded in [the venue cross-check](../evidence/east-kowloon-gap-fill-2026-10-21/venue-cross-check.md). Government works annotations are retained rather than interpreted as a guarantee that a venue is currently open.

## Integration

The game loads the integrated recreation data and separate Blender asset after Mong Kok recreation and before roadside decoration. Both regions' sport triangles share the terrain recreation mask. Existing Mong Kok data, fittings and play-pad behavior remain unchanged. All 27 park interiors and entrance corridors are reserved from later roadside decoration. Paving enters the shared terrain mask before street mesh completion, avoiding stacked ground meshes. The canonical recreation image retains its 8,192-pixel axis cap and 192 MiB RGB8 base-image budget. Normal play now uses the [compact recreation atlas](STARTUP_PERFORMANCE.md#sparse-recreation-mask--7-november-2026); explicit source checks regenerate the full image for the existing coverage assertions. Every canonical terrain image retains the [30 October allocation budget](STARTUP_PERFORMANCE.md), while the combined sparse recreation resources have a separate 32 MiB decoded-payload cap.

The running track keeps its sourced annular surface, while its enclosed athletics infield is reserved from authored paths and furniture. This also prevents garden generation from treating a sports polygon's inner ring as an empty planting bed.

The offline dataset and exported GLB keep runtime fully offline. Existing street trees, banyans and benches supply the planting and seating; no new image generation is required.

`Tools/import_east_open_spaces.py` reads the verified whole-sheet cache and manifest to regenerate the source and layout files. `Tools/check_east_open_spaces.py --bundled` verifies the shipped geometry, fitting containment, source hashes and fixture reuse regression. Pass `CACHE_DIR MANIFEST_JSON [PRESERVATION_BASELINE_DIR]` to also check official-index and archive hashes, exact Site and sports fragment multiplicity, deterministic regeneration and rejected refreshes. The archive checks remove a western sport fragment and one of Tsuen Wan Park's two patches on `6-SE-25B` and verify the saved outputs survive invalid refreshes. Run `build('east-kowloon')` from `Tools/model_open_spaces.py` through Blender MCP to export the integrated GLB and editable blend in an isolated scene. The default `build()` targets Mong Kok.

The strict fragment inventory expects all 59 Site and 135 sports patches, not only distinct IDs. A failed extraction or geometry review preserves both saved data files byte-for-byte. The complete previous 16-site source geometry, path/access/sample arrays, 1,505 fixtures, 71 surfaces and 50 fittings are checked against the Task 2 baseline. Every retained paving component keeps an interior connectivity sample with more than 1.1 m of edge clearance. For western sites, the generator also verifies that each retained path component reaches the public pavement network; where a component does not already connect, it tries a new entrance corridor using the existing 250 m limit and unchanged land/building/road/sports clearance rules. No western component was rejected in the final dataset. The game does not claim to show current construction access or venue opening status.

## Western-fill integration and final asset verification — 29 October 2026

The offline refresh checker passed deterministic regeneration and 27 rejected inputs (18 ZIP/manifest refreshes and nine saved-source/layout mutations), preserving both saved files. The previous 16-site snapshot remains exact: source features, site summaries, sports surfaces and fittings, garden/path/access/sample records, all 1,505 fixtures and all 44,518 paving triangles match the Task 2 baseline. Across the integrated 25 sites, the selected source contains 54 Site fragments and 135 sports fragments; Tsuen Wan Park's two Site patches and five multi-sheet sports outlines retain their separate fragments.

The 29 October headless integration suite exited 0 with 25 regional/approach drives, H1/H2/H3, 15 scheduled stops and 119 passengers. It also passed 133,749 full-bus envelope queries and the original 1.08 km driving/boarding check. This suite preceded the final Blender-only short-court paint adjustment. Its runtime and physics results remain applicable because runtime C# and data are byte-identical and all 88 collision meshes' attribute, index and material streams are exact. The suite does not validate the updated visual asset; the fresh native check below validates the final imported asset.

Kwai Chung's formerly disconnected retained path component now reaches public pavement through a 58.67 m corridor using the existing land, building, road and sports clearance rules. The final layout changes only Kwai Chung access, its added access sample and two paving triangles; site/path rings, path arrays, fixtures, sports surfaces and fitting records remain exact. Its access components increase from one to two, total path/access samples increase from 115 to 116, and paving triangles increase from 81,834 to 81,836. All 116 path/access samples connect across 25 sites.

The final native Mono Godot `--building-check` exited 0 after asset import. For reproduction, run `./run.command -- --building-check`; the exact executed Mono CLI invocation is recorded in `final-court-native-result.json`. The check passed 116 path/access samples, 120 sports probes, 116 ground-support probes, 861 infield probes, 3,068 fixture clearances, 54 reservations and 88 court colliders. Its 8,192 × 7,664 RGB8 recreation mask uses 188,350,464 bytes, below the 192 MiB cap. All 72 rendered terrain-boundary probes and asphalt-priority checks passed, with no engine errors or warnings. [Native result](../evidence/western-map-fixes-2026-10-28/final-court-native-result.json) and [engine log](../evidence/western-map-fixes-2026-10-28/final-court-native-building-check.log).

The short-court correction fixes marking overlap in the 4.8111 m-wide `1910085685` and 10.990 m-wide `1910085686` basketball fittings. Their length-aware markings keep at least 0.10 m between circle strokes and between free-throw circles and baseline strokes, and their keys do not cross midcourt. The in-build check validates all 23 BAC fittings; all 12 legacy BAC fittings and the other nine new BAC fittings retain their original marking parameters exactly. The narrow-width paint-containment check remains active. The final recreation GLB SHA-256 is `6129b5d06ac14a7ebf7e87d33d2c8cc9a6c43ca63b3bd9835ce6b1929e0014c2`; the editable Blender source SHA-256 is `941ef6956109c7019b020a20d2923b0c38b2cd84b00f5e88cacb4db30085c00e`.

The final model audit found exactly two changed visual meshes, 86 unchanged visual meshes, 88 exact collision meshes and all 100 prior world-position multisets exact without rounding or tolerance. Non-ground furniture on the adjusted courts is exact; all 216,432 audited vertices remain inside source outlines. Blender restored the prior scene, selection, active object and mode, and preserved Mong Kok assets. Evidence: [model audit](../evidence/western-map-fixes-2026-10-28/final-court-asset-audit.json), [Blender export](../evidence/western-map-fixes-2026-10-28/blender-final-court-fix.json), and [Blender log](../evidence/western-map-fixes-2026-10-28/blender-final-court-fix.log).

Final visual capture exited 0 with 17 HUD-free scenery views and one actual B/M game-map view, all 1,280 × 800, plus 11 matched before views. All 18 final images and 11 before images were inspected across six contact sheets; both revised Tsuen Wan Riviera courts were also inspected at full resolution. Their circle strokes are separated, their keys stay clear of midcourt, and no other new visual defect was found. The gallery's 66 local references are valid. [Before/after gallery](../evidence/western-map-fixes-2026-10-28/index.html), [capture result](../evidence/western-map-fixes-2026-10-28/capture-result.json), [capture log](../evidence/western-map-fixes-2026-10-28/capture-final-court-fix.log), and [short-court comparison](../evidence/western-map-fixes-2026-10-28/short-court-before-after.jpg).

The `.NET` build completed with zero warnings and errors. A final-fix-before comparison covers 479 products: 474 are byte-identical; the five changed files are the model-builder source, exported GLB, editable blend, README and this document. The source feature `LASTUPDATEDATE` values range from 2023-09-03 to 2026-08-06, and selected sheet revisions range from 29 July to 10 October 2026. Those dates do not establish current venue access. Manual interactive driving/reload stress and a performance benchmark were not repeated. Paths, entrances, planting, sports fittings, paving detail and flat terrain remain authored approximations rather than a surveyed reconstruction.

## Previous 16-site runtime snapshot — 28 October 2026, before the western fill

This recorded 16-site snapshot passed `Tools/check_east_open_spaces.py` with deterministic source/layout regeneration and 19 rejected-refresh byte-preservation cases (16 ZIP refreshes and three direct saved-source rebuilds). The regression removed the `1910085624` patch from one sheet while leaving its other three fragments in place. That layout reported 71 source sports outlines, 50 fitting records, 1,505 fixtures, 44,518 paving triangles and 72 connectivity probes. Preservation evidence compared the prior nine source boundaries, sports outlines, garden rings, path/access arrays, connectivity samples and fixtures with its before backup.

At that snapshot, the C# runtime checks expected 16 site IDs, 71 source sports outlines and all matching hidden fitting colliders. Blender MCP exported 50 court meshes and 50 collision meshes for those fittings and restored the original Blender scene; its export record is `evidence/wong-tai-sin-open-spaces-2026-10-28/blender-export.json`. The model audit confirmed all 50 visual/collision pairs and preserved the prior 25 fitting records and 50 visual/collision mesh-position sets; see `model-audit.json`. The `.NET` build exited 0 with zero warnings and errors.

The full headless suite for that snapshot exited 0: all 23 regional/approach drives, H1/H2/H3 services, the original 1.08 km steering/boarding loop, side-street turns and 133,581 full-bus envelope queries passed. The park check passed 72 paving/support and public-pavement connectivity probes, 71 sports probes, 437 clear infield probes, 1,505 clear fixtures and 50 court colliders. The native building check also exited 0, including all 72 rendered terrain-edge probes and final asphalt priority.

The final native capture for that snapshot exited 0 with ten matched scenery views, two extra overhead views and two keyboard-driven map screens. All 14 PNGs were directly inspected by its coordinator and reviewer. The Choi Hung close camera was obscured by a foreground building; its overhead view provided the placement evidence. [Before/after gallery](../evidence/wong-tai-sin-open-spaces-2026-10-28/index.html), [verification record](../evidence/wong-tai-sin-open-spaces-2026-10-28/verification.json), [independent review](../evidence/wong-tai-sin-open-spaces-2026-10-28/final-review.md).

That snapshot's 478-file preservation audit recorded 11 intended changes and 467 unchanged baseline files. Reload stress, manual interactive driving and a performance benchmark were not repeated. Paths, planting, surface finish and flat terrain remain authored approximations; source feature dates do not establish current venue access.

## Earlier verification snapshots

Initial-fill evidence, failing baselines, source refresh records and matched cameras are under `evidence/east-kowloon-gap-fill-2026-10-21/`. That full suite (`--headless --fixed-fps 60 -- --self-test`) exits 0: all 20 exploration/ramp drives, H1/H2/H3 services, both side-street turns and the original 1.08 km driving test pass. That run covered 37 paving/support samples, 38 sports samples, 437 clear infield probes, 792 fixtures and 25 court colliders. The eastern check also runs in the building and eastern exploration checks.

The initial source checker passed deterministic regeneration and 11 rejected-refresh preservation cases. Native capture exits 0 with nine matched views and no engine errors; all final views were inspected. Initial native building checks also passed 72 rendered Mong Kok play-pad edge probes and asphalt priority; those inputs and the shader remain unchanged after the infield correction. Build: **0 warnings / 0 errors**. All 173 pre-task data/assets retain their hashes, and independent re-review reports no remaining actionable findings.

Image inspection caught paths and furniture inside the running-track infield. The shared placement exclusion now protects the entire athletics enclosure; the failing regression and initial captures are retained alongside the corrected evidence. [Before/after gallery](../evidence/east-kowloon-gap-fill-2026-10-21/index.html), [verification record](../evidence/east-kowloon-gap-fill-2026-10-21/verification.json), [independent review](../evidence/east-kowloon-gap-fill-2026-10-21/independent-review.md).

Exact internal garden plans, swimming pools, detailed heritage features and current construction access are not reconstructed. Scene-reload stress testing and a performance benchmark were not repeated for this fill.

## 22 October review corrections

The importer now requires the complete reviewed set of 38 sports IDs in both the raw source and derived surfaces before replacing either saved output. The refresh regression removes football feature `1500001703` from a valid `11-NE-16C` ZIP and updates its manifest hash, then verifies rejection preserves both prior files. Additional cases remove a derived sports surface or a path-component probe.

The shared path generator joins the reported Hoi Sham and Kowloon Tsai islands across clear lawn, keeping all sourced sports surfaces, site boundaries, entrances and provenance unchanged. The rebuilt layout has 788 fixtures and all 37 original path/access probes. Pre-merge loop probes are retained after joining, so the former island interiors remain tested. Each retained paving component must have a probe; the in-engine check follows the actual paving mask from ground-level public roads to every probe, allowing one mask texel for linear filtering and excluding building interiors. This also retains valid connections through existing pavement. The earlier Tai Wan Shan edge passes within that filtering tolerance.

No Blender rebuild is needed: all 25 fitting records and all 38 sports surface records remain identical, as do the exported model and editable source. Existing map data and assets are preserved. Review-fix evidence is recorded separately in `evidence/east-open-space-review-fixes-2026-10-22/`.

The review-fix source checker passes deterministic regeneration and all 14 rejected-refresh preservation cases. The full driving suite exits 0 with all 20 regional/ramp drives, H1/H2/H3, both side-street turns and the original 1.08 km check. The final native run exits 0 with all 37 path/support probes, 38 sports samples, 437 clear infield probes, 788 clear fixtures and 25 colliders; it saves 11 inspected views and nine pavement-mask crops, including the complete Hung Hom entrance. Build: **0 warnings / 0 errors**. A fresh independent code review found no actionable defects.

The driving suite and final native run use identical geometry and fixtures. The saved driving-suite layout has 30 probes; the final native run exercises all 37 original pre-merge probes. The exact comparison is recorded in `layout-comparison.json`. The source snapshot, 25 fitting records and exported models remain unchanged; all 243 files outside the six intended edits retain their baseline hashes.

[Review-fix before/after gallery](../evidence/east-open-space-review-fixes-2026-10-22/index.html), [verification record](../evidence/east-open-space-review-fixes-2026-10-22/verification.json), [independent review](../evidence/east-open-space-review-fixes-2026-10-22/independent-review.md). These repairs reuse the verified nine-sheet snapshot; fresh downloads, scene-reload stress and performance testing were not repeated.

## 23 October fragment validation

Sports source IDs alone do not prove complete geometry: four reviewed sports outlines span two sheets. The importer now checks the exact 42 reviewed `(source ID, sheet)` patches for all 38 sports outlines, including multiplicity. Missing, duplicated or wrongly attributed patches reject before either saved output is replaced. The expected ID set comes from the same reviewed patch table. This shared validation runs for both whole-sheet refreshes and saved-source rebuilds.

The regression removes only football patch `1500001706` from `11-NE-21A`, keeps its other-sheet patch and all required archive layers/CRSs, and updates the ZIP checksum. Before the fix, this was accepted and lost 55.97 m² of unique source-derived geometry while replacing both saved datasets. The test now requires rejection and byte-for-byte preservation. Direct saved-source cases also exercise missing, duplicate and wrong-sheet patches; all test staging and destinations stay in temporary storage.

The patch table is the reviewed snapshot inventory. A legitimate government export that changes sheet membership or splits/merges a patch needs source review and an explicit inventory update before it can replace the bundled data. This guard does not claim surveyed internal garden layouts or current venue access.

The bundled source, layout, buildings, roads, services, C# runtime and models remain unchanged. No Blender export or new images are needed for this validation repair. Evidence is kept separately in `evidence/east-sports-fragment-fix-2026-10-23/`.

The final checker exits 0 with 18 rejected cases: 15 ZIP refreshes and three saved-source rebuilds. Both temporary input/output files retain their prior bytes after each rejection, and a complete refresh rebuilds byte-identical source/layout data. The failing pre-fix run is retained as `baseline.log`; the corrected run is `green.log`.

The fresh full in-engine suite exits 0 with all 20 regional/ramp drives, H1/H2/H3, both side-street turns, the original 1.08 km drive, all 37 path/support probes, 38 sports probes, 437 clear infield probes, 788 clear fixtures and 25 colliders. Build: **0 warnings / 0 errors**. Runtime content and all models remain unchanged, so native rendering and Blender export were not repeated. Fresh government downloads, scene-reload stress and performance benchmarks were also not repeated.

[Verification record](../evidence/east-sports-fragment-fix-2026-10-23/verification.json), [failing regression](../evidence/east-sports-fragment-fix-2026-10-23/baseline.log), [passing refresh checks](../evidence/east-sports-fragment-fix-2026-10-23/green.log), [full engine suite](../evidence/east-sports-fragment-fix-2026-10-23/self-test.log).

## Shared terrain initialization — 31 October 2026

Mong Kok initializes its bounds, play-area parameters, paving and fittings; the immediately following eastern builder creates the single combined recreation mask from both source datasets. The earlier standalone Mong Kok mask was never rendered and is no longer generated or uploaded. Native SHA-256 comparisons cover all three final terrain images and all their mip levels, with 44 matching records before and after this cleanup. Surface data, bounds and collision remain unchanged. See `evidence/allocator-memory-2026-10-31/` for the comparison and native checks.
