# Cross-Harbour Tunnel extension

The playable crossing follows the two Transport Department tunnel centrelines at the project's metre scale, from Hung Hom to the Hong Kong Island portal. The full map overview covers **2.44 km east–west × 3.34 km north–south**. Nathan Road's H1 service and its original district data stay intact.

Press **T while stopped** for a cab-view free drive from the Chatham Road approach. Follow the tunnel signs south, use the selected Wan Chai return roads, then take the northbound tube back to Kowloon. **M** shows both directions; **R** restarts H1. The same roads can also be reached through the existing street network. There are no passenger stops on the crossing yet.

## Government reference and scale

- Road data: © HKSAR Government / Transport Department, [Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2), [CENTERLINE.kmz](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz).
- [Transport Department tunnel details](https://www.td.gov.hk/en/transport_in_hong_kong/tunnels_and_bridges_n/location_map/index_t.html) describe the Cross-Harbour Tunnel as a dual two-lane connection between Hung Hom and Causeway Bay, approximately 1.9 km long.
- [The current data dictionary](https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip), `rdnet_dataspec_kml.pdf`, defines `ELEVATION` as a relative road level: negative values mean underground, positive values mean flyovers. It is **not a height or depth in metres**. `TRAVEL_DIRECTION=3` follows the digitised direction; `1` allows both directions.
- Reuse: [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions). Government ownership is acknowledged in this document, the README, data metadata and the HUD; no endorsement is implied.

`Data/cross-harbour-source.geojson` preserves 49 selected original WGS84 features and their source attributes. `Data/cross-harbour.json` contains sampled 3D paths, ground triangles, map bounds and provenance. The original KML altitudes are all zero; they are retained in the source file.

The derived southbound underground alignment is **1,856.8 m** in plan; the northbound alignment is **1,857.5 m**. The original Nathan Road coordinate origin remains `(114.17232° E, 22.2950° N)`, with +X east, −Z north and one unit per metre using the existing local geographic approximation. The crossing is neither compressed nor fitted to an arbitrary game-map size. Four-metre samples interpolate the original polylines; original source IDs remain available for review.

The enclosure also includes the existing 132.3 m southbound approach section and 208.3 m northbound exit section as authored ramps. This lets Salisbury Road remain at ground level above the crossing without steepening the tunnel. Total modeled enclosure lengths, including these ramps, are 1,989.1 m southbound and 2,065.8 m northbound; the government-coded underground alignments retain the 1,856.8 / 1,857.5 m lengths above.

The selected road chains are approximately 2.95 km southbound including the Kowloon approach, 1.44 km around the island return loop, and 3.73 km northbound including the Kowloon exit connection. Shared source sections are rendered only once.

## Authored parts and limits

The tunnel has an authored sinusoidal depth profile reaching **32 m below the district ground plane**, at most a 5.1% grade, and a **5.6 m interior height**. Each tube has a 7.3 m marked carriageway inside a 9.1 m shell; surface approaches are 12 m wide. These dimensions provide playable bus clearance and are not surveyed tunnel cross-sections. The bus follows the floor grade without a suspension or drivetrain simulation.

The island land apron, shoreline, background building blocks, portal frames, lights and signs are simplified scenery. This is a tunnel corridor extension, not a complete reconstruction of Wan Chai or the Hung Hom interchange. Selected surface-road levels are simplified; source travel directions are retained, but intersection turn restrictions have not been imported. No toll transaction, HKeToll equipment or additional traffic service is simulated.

The existing detailed Kowloon terrain mask stays at its original resolution. Only the portal openings are cut out of its ground mesh; deep tunnel sections pass below intact ground. Continuous buffered portal cuts prevent thin ground slivers across the roadway. Flat approach roads share the land collision surface; only the sloped tubes add road collision. The flat asphalt footprint is joined before triangulation to avoid overlapping road strips. Each tube is modeled continuously and resampled uniformly across source-section joins. Floor-triangle normals are asserted to catch folds caused by very short final source segments. Original city boundaries open only where the approach crosses them. Water is clipped around the land so it cannot draw through the shallow entrances. The building importer applies its existing 3.5 m road-clearance margin to the new surface approaches; this removes approximately 246 m² from the former massing, leaving 1,764 visible parts, 131 chunks and 723,737 m² of coverage. Original government building features remain unchanged.

Physics uses Godot 4.6's built-in Jolt engine and its enhanced internal-edge removal for movement queries. The default Godot solver reported false wall contacts at internal triangles of the flat ground on the Hung Hom exit bend; Jolt's native edge filtering resolves that reproducible case. See [Godot's Jolt documentation](https://docs.godotengine.org/en/4.6/tutorials/physics/using_jolt_physics.html). The retained exit-bend drive checks this alongside the tunnel ramps.

## Models and texture

Blender MCP executed `Tools/model_tunnel.py` in its own `Antila_CrossHarbour` scene, restoring the previously active scene afterward. It exports only that scene's selected objects to `Assets/Models/cross-harbour.glb`; the editable source is `Art/cross-harbour.blend`. Asphalt is reused from the existing game. Ceramic walls, raised service ledges, lane lines, lamps, reflectors and portal frames are original models.

The built-in imagegen tool generated `Assets/Textures/tunnel-tiles.png`. Exact prompt:

> Use case: photorealistic-natural. Asset type: seamless square albedo texture for a Hong Kong road tunnel wall in a 3D bus driving simulator. Flat orthographic close-up of aged off-white glazed rectangular ceramic tiles, each tile twice as wide as tall, laid in a perfectly regular straight grid. Thin warm gray grout, fine scratches, subtle diffuse road dust and tiny realistic chips, restrained dirt, clean enough to reflect tunnel lighting. Entire image is tile surface, identical even neutral illumination over the image, no directional shadows, no perspective, no edge frame, no signs, no text, no markings, no objects. Seamless repeat on all four edges. Approximately 4 tiles across and 8 rows. High detail photographic material scan, 1024 square.

## Regeneration and verification

```sh
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz
# Execute Tools/model_tunnel.py through Blender MCP.
.venv-geodata/bin/python Tools/import_buildings.py
# Execute Tools/model_government_buildings.py through Blender MCP.
./run.command --headless -- --harbour-check
./run.command --headless -- --self-test
./run.command --disable-vsync -- --harbour-review
./run.command -- --harbour
```

The importer asserts source IDs, travel direction at the reversed two-way connector, route continuity, tunnel plan lengths, portal opening clearance, continuous ground beneath all original street corridors and ground triangulation area. The in-engine check first repeats all 3,110 original-road clearance probes, exercises the T shortcut and its map/pause guards, tests chase-camera clearance below both tunnel roofs, 1,887 full-bus clearance envelopes across lane centres and road centrelines and drives the portal ramp, the Kowloon exit bend, both crossing directions and the island loop through the same steering/collision system used by the player. It rejects contacts and departures from the road. The full self-test includes the crossing and the original city/service checks.

Verified on 13 September 2026 with Godot 4.6.2 .NET and a C# build of **0 warnings / 0 errors**:

- `evidence/harbour/check.log`: exit 0; 3,110 original-road probes and 1,887 crossing bus envelopes; map/pause guards and cab shortcut; both tunnel chase cameras; 218 m portal-ramp and 621 m exit-bend drives; 2,933 m southbound, 1,442 m island loop and 3,721 m northbound driven without contacts. Both crossings reach −32 m.
- `evidence/harbour/self-test.log`: exit 0; the same crossing checks plus road paint, 54 building-roof probes, pavement access, audio, map/camera/traffic regressions, 14 signal junctions, physical reverse and the deliberate boundary-impact check. Haiphong Road (366 m), Granville Road (790 m) and the full H1 service (1.08 km, three stops, 26 passengers) all complete without unintended contacts.
- `evidence/harbour/restart.log`: Godot input-event smoke check confirms that `--harbour` starts free drive and the restart action reloads H1.
- `evidence/harbour/review.log`: native OpenGL render completed and saved six views: Hung Hom portal, tunnel interior, island exit, harbour overview, driving cab and full map. These are actual game renders. Native keyboard input was not rechecked because desktop automation reported the Mac locked; shortcut checks used the engine input path.
- The regenerated Blender GLB contains 70 objects and two continuous tube floors, 7.44 MiB. The importer also checks that all original street corridors retain continuous ground after the portal cuts.

The focused/restart runs printed Godot's ObjectDB/resource-in-use shutdown diagnostics while exiting 0. The final full self-test and native render exited 0 without those diagnostics. `evidence/harbour/play.log` records the game left open at the approach. No performance benchmark is claimed.
