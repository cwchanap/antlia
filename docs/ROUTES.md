# Bus routes and trip results

The game opens on a route select screen. Pick a service, read its briefing, drive it stop by stop and finish at its terminus. A results screen then reports the trip. Free drives remain on the same screen for exploring without stops or scoring.

All three services are fictional. Route numbers, stop names, stop placements and waiting passengers are authored prototype data, not published bus routes, timetables or surveyed bus stops. Stop names reference a nearby street in the bundled Transport Department centreline data.

## Services

| Route | Name | Length | Stops | Passengers | Geometry |
| --- | --- | --- | --- | --- | --- |
| H1 | Tsim Sha Tsui → Jordan | 1.15 km | 3 | 26 | The original Nathan Road corridor in `Data/nathan-road.json`, lane −7.3, signals and taxis |
| H2 | Jordan → Mong Kok → Sham Shui Po | 3.88 km | 8 | 60 | Harbour drives 5 and 7 joined: Nathan Road north, Cheung Sha Wan Road, Yen Chow Street, Yu Chau Street, Pei Ho Street |
| H3 | Hung Hom → Wan Chai | 3.43 km | 4 | 33 | Harbour drive 0 (Hong Chong Road, the Cross-Harbour Tunnel) and the first 480 m of drive 1 (Hung Hing Road) |

`Data/routes.json` holds the table. A leg is either `{"nathan": lane}` (the H1 corridor and its stops) or `{"drive": n, "to": metres}` (a government-derived drive from `Data/cross-harbour.json`, optionally cut short). Stop distances are metres along the joined route.

| H2 stop | Chinese | Distance | Furniture | Passengers |
| --- | --- | --- | --- | --- |
| Saigon Street | 西貢街 | 155 m | shelter | 6 |
| Waterloo Road | 窩打老道 | 765 m | pole | 9 |
| Shantung Street | 山東街 | 1,270 m | shelter | 12 |
| Bute Street | 弼街 | 1,940 m | shelter | 10 |
| Wong Chuk Street | 黃竹街 | 2,727 m | shelter | 7 |
| Cheung Sha Wan Road | 長沙灣道 | 3,110 m | shelter | 8 |
| Kweilin Street | 桂林街 | 3,550 m | pole | 5 |
| Pei Ho Street (terminus) | 北河街 | 3,850 m | shelter | 3 |

| H3 stop | Chinese | Distance | Furniture | Passengers |
| --- | --- | --- | --- | --- |
| Hong Chong Road | 康莊道 | 435 m | shelter | 9 |
| Tunnel Interchange | 紅隧轉車站 | 770 m | shelter | 14 |
| Hung Hing Road | 鴻興道 | 3,040 m | shelter | 6 |
| Marsh Road (terminus) | 馬師道 | 3,388 m | shelter | 4 |

## Playing a route

| Screen | Keys |
| --- | --- |
| Route select | Up / Down or 1–3 choose, Enter opens the briefing, a click selects a card. T, I, J, K, L, N, B, U and O start the free drives. |
| Briefing | Enter starts, C picks chase or cab view, Escape returns. |
| Driving | Tab ends the route early. R restarts the same route. Escape pauses. |
| Results | R drives the route again, Enter or Tab returns to route select. |

Pull into the green bay, stop with the bus aligned to the road and press E. Boarding takes four seconds, then close the doors and continue. A stop left more than 30 m behind counts as missed so the trip can go on; the terminus can never be missed. Serving the terminus ends the trip. A banner warns of each junction turn on the route from 220 m ahead.

The results screen shows journey time, distance actually driven, average speed, stops served and missed, passengers boarded, bay accuracy (the mean distance from the bus centre to the stop mark when boarding finished), contacts and red-light crossings, with a per-stop table. Signals and taxis exist only on the original Nathan Road and Tsim Sha Tsui junctions, so H2 and H3 have no signals or traffic.

## How the new routes are laid out

The harbour roads are government centrelines given authored widths: 12 m on the ground, 6 or 12 m on decks, and 7.3 m between the tube ledges. Bus lanes are fitted from those widths, not from surveyed lane markings.

- **Reference line.** Centrelines jog several metres through junctions. H2 and H3 run on a line averaged over ±8 m with its normal taken from a 20 m chord, so a large lane offset does not jump at a jog. H1 keeps RoadMap's exact 5 m stations.
- **Kerbside lane.** Every 2.5 m the fit scans left for the first 2.5 m of ground that no same-level carriageway covers. That edge plus 2.4 m is the running lane. Painted gaps under 2.5 m between twin carriageways are crossed: a harbour street lamp needs 2.6 m, so none stands in a narrower gap. Nathan Road north of Jordan is two parallel centrelines in the data, so H2 runs about 15 m left of its own centreline there.
- **Hard edges.** In a tube the lane is the left lane (−1.85 m), and on a deck it keeps 1.55 m inside the edge, for a bus length either side so the body is inside before a portal.
- **Smoothing.** A ±25 m median removes junction mouths, inside-turn offsets are capped to leave an 11 m turning radius, and lane changes are limited to 0.12 m per metre, always resolved toward the line.
- **Stops.** A bay sits 0.4 m nearer the kerb than the running lane. A shelter needs clear pavement 4.9 m beyond the bay centre; where Mong Kok pavements are narrower, a flag pole stands beside the bay door and the queue waits 3.3 m out. Sites must be clear of building footprints, harbour scenery and other carriageways.

`--stop-survey` prints the fitted lane every 25 m and every 5 m stretch that is straight, at ground level, steady in lane and has pavement for a shelter (S) or a pole (P). The stops above were chosen from that output.

## Reproduce checks and views

```sh
./run.command --headless -- --route-check            # data, menu flow, missed stop, abandoned trip, then H1, H2 and H3 driven
./run.command --headless -- --route-check --route=H2 # the same, driving only H2
./run.command --headless -- --stop-survey            # candidate stop sites and fitted lanes for H2 and H3
./run.command -- --route-capture                     # evidence/routes/*.png: menu, briefing, staged bays, tube, H2 map, H1 results
./run.command --headless -- --self-test              # includes --route-check after the harbour drives
```

`--route-check` asserts the route table (three services, H1 identical to Nathan Road, lengths 3,879 m and 3,431 m, 8 stops / 60 passengers with two poles on H2, 4 shelters / 33 passengers on H3, three junction turns each, and stop labels on the expanded map that stay inside it, above its footer). It steps the menu with the same input actions as play, skips a stop to prove the missed-stop rule, abandons H2 with Tab, then drives every route with the player's controller. A scripted driver steers by pure pursuit, brakes for bends, bays and red signals, and opens the doors at each bay. Each drive must serve every stop with no contact, no red-light crossing and no lane departure over 3.5 m, finish at the terminus, and stop within 3 m of every mark. H3 must descend below −30 m in the tube.

`--route-capture` stages the bus at bays for its stills; only `results-h1.png` follows a driven trip.

## Limits

Lane positions come from authored road widths, so H2 runs on the left of the combined twin-carriageway asphalt rather than a surveyed northbound lane. It moves toward the line before tight left turns. There are no other buses, timetables, fares, passengers alighting, or traffic on H2 and H3. The scripted test driver proves the routes can be driven cleanly; it is not a player benchmark.

## Verification — 17 October 2026

Runs used Godot 4.6.2 .NET on Linux in a cloud container. Captures used Xvfb with Mesa llvmpipe software rendering at 1440×900.

- Build: **0 warnings / 0 errors**.
- `--self-test` exits 0 with `ANTILA_SELF_TEST_OK`. That covers the existing road, building, footpath, audio, HUD, signal and harbour-drive checks, then `--route-check`, then the original H1 service. The route drives were:
  - H1: 1,078 m in 267 s of trip time, 3 stops, 26 passengers.
  - H2: 3,752 m in 553 s, 8 stops, 60 passengers.
  - H3: 3,373 m in 432 s, 4 stops, 33 passengers, below −30 m in the tube.

  None of the drives had a contact or a red-light crossing. The scripted driver brakes to halt about 2 m short of each mark, so every bay offset reads 2.0 m. Trip times are the game clock under the check's time scale, not a benchmark.
- That suite ran before the destination-blind overlays were added. With the overlays in place, the driven H1 trip in `--route-capture` also completed. `--route-check` was then repeated on the final build and exited 0. It gave the same distances, stops and passengers, with no contacts, no red-light crossings and no engine errors logged.
- `--restart-check --fixed-fps 60` exits 0 with `ANTILA_RESTART_CHECKS_OK`. All seven reloads keep 4,912 building meshes and 2,456 collision shapes, with no engine errors. An earlier run without `--fixed-fps`, made while a capture run was also using the machine, logged 72 `Handle is not initialized` errors. They came while government buildings were instanced on the second reload. That is the intermittent Godot/.NET handle issue described under [Restart cleanup](ISLAND_EXPANSION.md#restart-cleanup--22-september-2026), at the same call site. The building instancing code is unchanged here, and one clean rerun does not prove the issue gone.
- `--route-capture` saved eight images in `evidence/routes/`, and all eight were inspected. `evidence/` is git-ignored, so they are not committed. Three show route select, the briefing and the results after a driven H1 trip. The other five are staged:
  - the Waterloo Road pole stop
  - Mong Kok from the cab
  - Yu Chau Street
  - the Tunnel Interchange shelter
  - the tube from the cab

## Review follow-up — 17 October 2026

- **Expanded-map legend.** On the M map, H2's eight stop labels started at y=600 and ran down into the footer lines at y=759 and y=784. Routes with up to five stops keep the old placement; longer routes now start their list higher so it ends inside the map. `--route-check` asserts every route's labels sit inside the map with at least 20 px between them, and `--route-capture` adds `h2-map.png`.
- **Capture boarding.** `--route-capture` is not a self-test launch, so `_Process` advanced the service as well as the scripted driver, and each stop in `results-h1.png` boarded in about 2 s instead of 4 s. The capture now sets `SelfTest`, as `--capture` already did.
- `--route-check` passed after the legend change. Build: **0 warnings / 0 errors**.
