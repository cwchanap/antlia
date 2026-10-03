# Asset detail review — 20 September 2026

Originally reviewed revision `dbc1bf1` in Godot 4.6.2 Mono, GL Compatibility. No game code, models or textures changed during that review. The approved fixes are recorded in [the implemented follow-up](#implemented-follow-up--20-september-2026) below. Original evidence is local under `evidence/asset-review-2026-09-20/`, which the repository deliberately excludes from Git.

## Findings, in recommended order

### 1. Tunnel sunlight leaks through the enclosure

At a camera position about 29 m below ground, an enclosed road segment has a bright triangular sunlight patch. See [current rendering](../evidence/asset-review-2026-09-20/tunnel-interior.png).

The ceiling is a single strip with reversed winding in `Tools/model_tunnel.py:130`. The runtime imports it without changing shadow casting in `Scripts/Main.Harbour.cs:27`. A runtime-only comparison changing ceiling meshes to double-sided shadow casting removes the nearby patch: [comparison](../evidence/asset-review-2026-09-20/tunnel-double-sided-shadow.png). Disabling the directional sun removes both the nearby patch and distant glare: [sun disabled](../evidence/asset-review-2026-09-20/tunnel-no-sun.png).

The double-sided change alone is **not a complete fix**: distant glare remains. The sun has a 170 m shadow distance (`Scripts/Main.cs:148`), consistent with that remaining symptom, but the distance setting was not independently varied. Correct the ceiling shadow mode and handle directional sunlight inside the tunnel; validate both travel directions and portal transitions. These diagnostic changes were not saved to the game.

### 2. Open bus doors expose a solid backing

The animated door leaves move, but the entrance remains a solid dark rectangle: [open doors](../evidence/asset-review-2026-09-20/bus-doors.png). `Tools/model_assets.py:179` creates a permanent backing behind the moving `Door_*` objects. The lower body and window bands also span the entire vehicle (`Tools/model_assets.py:161–166`).

Model a real opening with a small stepwell and entrance interior, preserving the existing door nodes and animation. Removing only the black backing would still leave the solid body underneath. This is more noticeable during boarding than adding small exterior trim.

### 3. Shelter glazing renders as an opaque wall

The shelter's large rear pane is completely opaque: [shelter](../evidence/asset-review-2026-09-20/shelter.png). The shared `glass` material uses alpha 1 and the exported GLB uses opaque rendering (`Tools/model_assets.py:17–33,281`).

Give shelter glazing its own tinted transparent material. Do not indiscriminately change the shared bus material: the bus currently has solid window volumes and no finished passenger interior. Check the shelter from both sides, including overlapping panes and passengers.

## Larger art improvements

| Area | Observed limitation | Smallest useful next pass |
| --- | --- | --- |
| Building fronts | One cafe image repeats across frontage sections; windows, balconies and air conditioners are printed on flat walls. Four tint materials share one facade atlas. [Corner view](../evidence/asset-review-2026-09-20/building-corner.png), [street view](../evidence/asset-review-2026-09-20/street-level.png). | Vary ground-floor shopfronts first, then add a few recessed entrances, awnings and air conditioners along the driven route. Preserve the government footprints. The repetition comes from `Tools/model_government_buildings.py:41–45,70–89`. |
| Bus cab | Dashboard and steering assembly remain simple primitives, with little instrument or surface detail. [Cab](../evidence/asset-review-2026-09-20/cab.png). | Add readable instruments and a coherent dashboard material before increasing exterior polygon counts (`Scripts/Main.cs:430–442`). |
| Island scenery | The return loop faces plain box towers and largely undecorated ground. [Island loop](../evidence/asset-review-2026-09-20/island-loop.png). | Apply existing facade materials and add route-edge street furniture. The 22 towers are explicitly authored placeholders (`Scripts/Main.Harbour.cs:51–60`), not imported building footprints. |
| Trees and passengers | The same tree silhouette and static passenger poses recur at stops. [Foliage](../evidence/asset-review-2026-09-20/foliage.png), [passengers](../evidence/asset-review-2026-09-20/passengers.png). | Add a few canopy shapes and passenger poses after the defects above. Existing leaf cutouts and scanned clothing detail already read well at normal driving distance. |

## What holds up

Pavement surfaces, tactile paving, drains, railings and road markings give the street useful close-range detail. Passenger proportions and clothing are substantially more natural than the current bus and cab. Building massing provides a dense skyline; facade variety and depth are the more visible constraints now.

The [GLB inventory](../evidence/asset-review-2026-09-20/inventory.json) covers all 20 model files on disk, including the three older shop models and locally licensed passenger assets. It is not a list of simultaneously rendered assets. None of those GLBs uses normal-map or metallic/roughness textures; roughness and metallic values are constants. Selective material detail could help close surfaces, but this inventory is not evidence of a performance problem. No performance benchmark was run.

## Verification and reproduction

- Fresh C# build: **0 warnings, 0 errors**.
- Fresh `--building-check`: passed road clearance, markings, pavement fill, building geometry/UV and footpath checks. It includes 1,764 building parts, 131 spatial chunks and 54 roof collision probes. [Engine log](../evidence/asset-review-2026-09-20/check.log).
- Captured and inspected **16 current-scene views**, plus two tunnel lighting variants. [Capture log](../evidence/asset-review-2026-09-20/capture.log), [lighting log](../evidence/asset-review-2026-09-20/lighting-probe.log).
- The harness hides the HUD, pauses gameplay and positions the camera for inspection. The lighting probe makes temporary in-memory changes only. These are still captures, not a fresh full driving-suite or animation review.

From the repository root, with the local evidence scripts present:

```sh
./run.command --headless --log-file "$PWD/evidence/asset-review-2026-09-20/check.log" -- --building-check
/Applications/Godot_mono.app/Contents/MacOS/Godot --path "$PWD" --disable-vsync --script res://evidence/asset-review-2026-09-20/capture.gd --log-file "$PWD/evidence/asset-review-2026-09-20/capture.log"
/Applications/Godot_mono.app/Contents/MacOS/Godot --path "$PWD" --disable-vsync --script res://evidence/asset-review-2026-09-20/lighting-probe.gd --log-file "$PWD/evidence/asset-review-2026-09-20/lighting-probe.log"
```

Rerunning these commands replaces this review's local evidence files. No full driving regression suite was rerun because the review did not modify gameplay or assets.

## Implemented follow-up — 20 September 2026

The approved follow-up fixes the three defects and applies the first bounded art improvements:

- Both tube interiors are excluded from direct sunlight using render layers; double-sided roof shadows remain enabled. Bus and cab lighting follows the tunnel envelope and restores outdoors. This fixes the distant glare as well as the nearby patch.
- Both bus doorways have actual body cutouts, three steps, yellow nosings and handrails. Front entrance/axle spacing now clears the wheel, and the tactile paving follows the corrected door offset. Sliding doors and the movement interlock remain in place.
- Shelter panes use a separate transparent material and do not cast opaque glass shadows. Bus glazing is unchanged.
- Four new generated storefronts alternate with the cafe, with 18 cm recesses and modeled reveals. All **131 building collision chunks are identical** to the reviewed version: [collision fingerprints](../evidence/asset-fixes-2026-09-20/collision-parity.json).
- The cab displays live speed, drive/reverse and door status. Island towers reuse the facade atlas at a fixed window scale, with roof caps, lamps and planters along the return loop.

Blender MCP regenerated the bus, shelter and government-building GLBs. Editable changes are in `Art/bus-stop-details.blend` and `Art/kowloon-buildings.blend`; the old GLBs are backed up in `Art/before-asset-fixes-2026-09-20/`. The built-in imagegen tool supplied `Assets/Textures/shopfront-variety.png`; [the exact prompt and dimensions](REALISM_ASSETS.md) are recorded with the asset.

The first final capture set contains 24 native Godot views, including both tube directions and a driver view of the island loop. Compare the original review images above with:

| Change | Current render |
| --- | --- |
| Tunnel lighting | [Same review camera](../evidence/asset-fixes-2026-09-20/tunnel-interior.png), [northbound](../evidence/asset-fixes-2026-09-20/northbound-deep.png) |
| Door geometry | [Entrance close-up](../evidence/asset-fixes-2026-09-20/entrance-close.png) |
| Shelter glass | [Kowloon Park shelter](../evidence/asset-fixes-2026-09-20/shelter.png) |
| Frontage variety | [Nathan Road](../evidence/asset-fixes-2026-09-20/building-front.png) |
| Cab instruments | [Stopped with doors open](../evidence/asset-fixes-2026-09-20/cab.png) |
| Island detail | [Return-loop driver view](../evidence/asset-fixes-2026-09-20/island-driver.png) |

[Side-by-side comparison page](../evidence/asset-fixes-2026-09-20/compare.html). Eight additional cab captures check the position-based lighting switch just outside and inside all four portals; [portal check log](../evidence/asset-fixes-2026-09-20/portal-check.log) exits 0. Outdoor scenery retains daylight while the cab enters shade, then restores on exit. The capture runs report no engine warnings or errors.

`CheckAssetDetails`, included in `--building-check` and `--self-test`, checks both tunnel lighting layers, vehicle daylight restoration, imported entrance/step geometry, wheel clearance and shelter alpha mode. The entry-edge rays stop before the intentionally modeled grab rails.

The first test iterations caught Godot importing glTF glass with opaque shadow casting and an overlong clearance probe hitting the intended handrail. The runtime import mode and probe boundary were corrected after inspecting the imported materials and exact hit triangles. Historical iteration logs remain under the evidence folder.

Final verification: C# build **0 warnings / 0 errors**. `./run.command --headless --verbose --log-file "$PWD/evidence/asset-fixes-2026-09-20/self-test-verified.log" -- --self-test` exited **0**, with the new asset checks, existing scenery/audio/signal/camera checks, 1,887 harbour clearance probes, both tunnel crossings, island loop, portal ramp, exit bend, Haiphong and Granville drives, and the original **1.08 km H1 service / three stops / 26 passengers**. All routes completed without unintended contacts; the deliberate boundary-impact check still runs. [Final full-suite log](../evidence/asset-fixes-2026-09-20/self-test-verified.log). The final full-suite run has no engine errors or resource-leak shutdown diagnostics.

Remaining art limits: there is no full passenger interior, functioning mirror view, animated passenger set or new tree variants. Upper-floor detail remains primarily albedo-based. The island remains authored corridor scenery rather than a surveyed district reconstruction. No performance benchmark is claimed.
