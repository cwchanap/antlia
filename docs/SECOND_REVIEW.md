# Second game review

This pass checks driving behavior after the road and building polish. The pre-fix run reproduced the three behavioral findings in `evidence/before-second-review/regressions.log`.

| Finding | Fix |
| --- | --- |
| E and Q still changed doors and gear behind the paused map. | The shared action guard now blocks bus controls while the map is open. Closing a map opened from Pause preserves Pause. |
| The chase camera entered a building when the bus faced across Nathan Road. | Sweep a camera-sized sphere from above the bus to the smoothed camera position, pulling the camera forward at walls. The cab position is preserved. |
| The cab notification overlapped the next-stop panel. | Move it into the clear horizontal space beside the panel. |
| Ambient taxis were repositioned every rendered frame and passed through a stationary bus. | Advance each taxi on physics ticks only when its body can move safely. It waits at an obstruction and resumes after clearance; looping also checks the destination. |

The key-binding audit found Godot already deduplicates repeated arrow bindings; no input-registration change was needed. Road data, building density and art assets are unchanged in this pass.

## Verification

Run `./run.command --headless -- --self-test`. The retained review check covers map controls and nested pause, camera obstruction and smoothing, the unobstructed chase/cab positions, taxi approach/wait/resume, traffic pausing with the map, and occupied/clear loop destinations. It also runs the existing clearance, side-street driving and full three-stop service checks.

Run `./run.command -- --capture` for the normal views plus `evidence/camera-wall.png`, taken at the previously obstructed pose. The earlier rendered views are retained in `evidence/before-second-review/`.

- C# builds completed with zero warnings and errors.
- All new regression checks passed.
- All 3,110 static road-clearance queries passed.
- Physically drove 366 m on Haiphong Road and 790 m on Granville Road without contacts.
- Completed the 1.08 km H1 run with three stops, 26 passengers and no route contacts.
- Fresh rendered chase, cab, intersection and wall-obstruction views were inspected; no recurrence of the prior broken road surfaces was visible.

Native checks also passed in the final launched build: M opens the map; E/Q leave Drive and closed doors unchanged while it is open; Escape closes it; opening/closing the map from Pause preserves Pause. E/Q work again after resuming, C switches to the cab, and F12 saves the view. The final `evidence/cab.png` confirms the notification is clear of the next-stop panel. The game is left running in Drive with closed doors.

![Camera pulled forward at the wall](../evidence/camera-wall.png)

![Cab notification clear of the stop panel](../evidence/cab.png)

## Scope

The camera uses existing physical building geometry; decorative signs and foliage remain visual-only. Taxis still follow one fixed-speed southbound lane and stop abruptly; junction decisions and smooth braking remain outside this prototype pass. Building repetition, approximate lane widths and the flat map boundary remain visible art limitations.

The implementation uses Godot 4.6 native [shape sweeps](https://docs.godotengine.org/en/4.6/classes/class_physicsdirectspacestate3d.html#class-physicsdirectspacestate3d-method-cast-motion) and [body movement checks](https://docs.godotengine.org/en/4.6/classes/class_physicsbody3d.html#class-physicsbody3d-method-test-move).
