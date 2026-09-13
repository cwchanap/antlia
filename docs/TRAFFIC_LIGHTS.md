# Traffic lights

Fourteen authored junctions provide 48 incoming approaches and 96 signal heads, each approach with a kerbside signal and a far-side repeater. Placements follow the bundled government road alignment. Stop lines and crossing boundary studs replace the old zebra paint at the controlled Haiphong, Cameron and Jordan junctions.

| Area | Controlled junctions |
| --- | --- |
| Nathan Road | Peking, Mody, Carnarvon, Haiphong / Humphreys, Cameron, Granville, Kimberley, Hillwood, Austin, Jordan |
| Canton Road | Haiphong, Austin / Austin Road West |
| Chatham Road South | Granville, Mody |

The expansion adds nine junctions and 31 approaches. Named-road projection reuses `RoadMap.NearestStreet`; approaches beyond the H1 endpoint use the full physical road centreline so the Jordan signals are not clamped to the service-route end.

Signal poles use the nearest clear kerb location around their intended position, checking the combined road footprint and building lots and keeping at least three metres between poles. This keeps repeaters out of lanes at skewed crossings and split carriageways. The in-engine check also verifies all 96 poles clear the road and building collision bodies.

The signal model was created through Blender MCP with `Tools/model_traffic_signal.py`. `Art/traffic-signal.blend` retains the editable isolated scene; `Assets/Models/traffic-signal.glb` contains only its 11 meshes (about 100 KB), with three separately controlled lenses, a pale backing border and open sun hoods. Existing Blender scenes are preserved.

The player brakes manually. The HUD shows the next applicable signal within 95 m, with distance measured from the front of the bus. Crossing a red or red-and-amber stop line triggers a warning and increments the completion summary. Resets do not count as movement. Amber crossings are not penalized. Taxis stop with their front bumper 1.2 m behind the line and resume on green; existing obstacle and occupied-loop checks still apply. Pause, map and service completion freeze the signal clock with traffic.

Red-and-amber continues to mean stop; green allows proceeding only when the junction is clear. This follows the [Transport Department's Road Users' Code](https://www.td.gov.hk/en/road_safety/road_users_code/index/chapter_5_for_all_drivers/traffic_light_junctions_/?print=1). [Amber means stop unless already too close to stop safely](https://www.info.gov.hk/gia/general/201101/05/P201101050114.htm).

These are prototype placements and timings, not surveyed signal installations or live traffic data. Each junction repeats a 54-second cycle, with authored offsets stored beside each junction in `Scripts/Main.Signals.cs`:

| Cycle seconds | Main road | Cross road |
| --- | --- | --- |
| 0–24 | Green | Red |
| 24–27 | Amber | Red |
| 27–29 | Red | Red |
| 29–31 | Red | Red + amber |
| 31–47 | Red | Green |
| 47–50 | Red | Amber |
| 50–52 | Red | Red |
| 52–54 | Red + amber | Red |

Turning drivers must yield to oncoming traffic. There are no protected turn arrows, pedestrian phases, demand sensors or cross-street AI vehicles. Taxis retain their simple fixed-speed lane-following movement and abrupt stops.

## Reproduce checks and views

```sh
./run.command --headless -- --self-test
./run.command --headless -- --signal-check
./run.command -- --signal-capture
```

The existing in-engine check verifies all 48 approaches are aligned with roads, selected correctly from their incoming lanes, and extend to Canton, Chatham and Jordan. It also covers the full cycle and transition boundaries, nonconflicting greens, front-bumper red/red-and-amber crossings, opposite-lane and reset rejection, lit-lens materials, taxi approach/hold/restart and pause/map/completion freeze. The physical route driver obeys the signals; the Granville right-turn check also waits for oncoming taxis before entering. The existing road-clearance, audio, service and side-street checks remain enabled.

`evidence/traffic-expansion-test.log` records the expanded driving checks; `evidence/traffic-placement-check.log` records the focused signal, pole-clearance, audio and pause/traffic regression checks after the final pole-spacing adjustment. `evidence/traffic-expansion-capture.log` and `signal-red.png`, `signal-red-amber.png`, `signal-green.png`, `signal-amber.png` and `signal-junction.png` show actual Godot renders. The additional `signal-peking.png`, `signal-canton.png`, `signal-chatham.png` and `signal-jordan.png` show the expanded coverage. Capture mode holds a fixed bus pose and signal clock to compare the four aspects.

Initial five-junction pass verified on 12 September 2026: C# built with zero warnings/errors; signal checks and all 3,110 road-clearance queries passed. The bus drove 366 m west via Haiphong and 790 m east via Granville, then completed the 1.08 km service with 26 passengers, no new contacts and no red-light crossings. All four aspects and the repeaters were inspected in rendered cab/street views.

Expanded coverage verified on 12 September 2026: the complete 1.08 km service and both side-street drives passed with no new contacts or red-light crossings. All 48 approach directions, 96 pole clearances, signal phases, taxi stops/restarts and pause states passed. The final C# build had zero warnings/errors.

Short-run shutdown initially failed inside Godot 4.6.2 C# instance-binding finalization. Automated exits now collect temporary managed resource wrappers and wait for their finalizers while the engine is still alive, before requesting shutdown. The focused check and final rendered capture both passed and exited cleanly after this change.
