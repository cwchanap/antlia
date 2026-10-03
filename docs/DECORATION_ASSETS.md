# Vegetation and street decoration

## Bus and shelter corrections — 20 September 2026

Blender MCP regenerated `bus.glb` and `shelter.glb` using `Tools/model_assets.py` with `ONLY_BUS_STOP=True`; `Art/bus-stop-details.blend` holds these revised editable assets. The generator restores the previous Blender scene even if generation fails. The existing `Art/antila-assets.blend` remains the earlier full collection; rerunning the full generator also includes the corrections.

Both bus entrances now cut through the body and lower glazing, with three modeled steps, yellow nosings, handrails and inset vestibules. The front entrance moves to 4.2 m ahead of the model origin and the front axle to 3.0 m for wheel clearance. Front-door tactile paving follows the new offset. Animated `Door_*` nodes and all six `Wheel_*` nodes remain separate. There is no full passenger cabin or walking/boarding animation.

The shelter uses three single-surface tinted panes, alpha 0.22, with clamp rails and visibility strips. Its separate glass material exports as glTF `BLEND`; the runtime selects Godot's ordinary alpha mode so the panes do not cast opaque shadows. Bus glazing keeps its existing material.

The existing planter mesh is also reused beside the island loop, with street lamps and road-clearance exclusions. Trees and passenger poses are unchanged. See [review follow-up](ASSET_DETAIL_REVIEW.md) for checks and rendered comparisons.

Created with Blender MCP and the built-in imagegen tool on 12 September 2026.

The banyan model uses tapered branches, buttress roots, hanging aerial roots and 112 static leaf cards with a double-sided alpha-cutout material. The same foliage texture supplies the small planters. Benches and orange litter bins are modeled meshes. All are original approximations for this scene.

The tree silhouette is informed by the [Hong Kong Zoological and Botanical Gardens Chinese banyan description](https://www.hkzbg.gov.hk/en/plants/tree/archsdcw6.html). Generated textures are original images, not photographs of that tree.

## Saved assets

- `Assets/Textures/banyan-leaves.png`: transparent leaf spray, used by the tree and planters.
- `Assets/Textures/banyan-bark.png`: bark albedo, UVs follow the branch length.
- `Assets/Textures/park-ground.png`: lawn albedo, two-metre repeat along the park.
- `Assets/Models/banyan.glb`, `bench.glb`, `bin.glb`, `planter.glb`: exported models, with images embedded where used.
- `Art/antila-assets.blend`: editable source scene with packed images.

The canopy uses alpha cutouts rather than blended transparency. It is static; there is no wind animation. Props are decorative and do not add collision bodies. Boarding zones remain clear. The lawn is a flat textured surface.

All three saved PNGs are 1254 × 1254. The leaf alpha channel was checked for both transparent and opaque pixels. Exported tree and planter materials were checked for `alphaMode: MASK` and double-sided rendering. The tree has 1,924 triangles. Model exports assert valid, finite UVs. The final in-game views were visually inspected; `evidence/park-before-decoration.png` retains the earlier park for comparison.

## Generation prompts

### banyan-leaves

Use case: photorealistic-natural. Asset type: alpha-cutout foliage texture for layered 3D tree canopy cards in a Hong Kong bus simulator. Create a square photorealistic close view of ONE dense small spray of Chinese banyan foliage, roughly 50 to 70 small oval pointed leathery leaves on slender branching twigs. Natural irregular broad rounded silhouette, with many transparent gaps between leaves and twig stems. Deep olive and medium fresh green leaves, realistic fine veins, subtle waxy highlights, a few lighter new leaves. Flat straight-on botanical photography, diffuse daylight, sharp leaf edges and all leaves in focus. The foliage fills 88 percent of the square, keep a clear margin all around, entire spray visible. IMPORTANT: actual transparent RGBA background and actual transparent gaps between leaves, no checkerboard pattern, no solid background, no ground, no tree trunk, no pot, no text, no shadow outside the leaves. This will be placed on multiple intersecting 3D cards, not used as a picture of a complete tree. Real leaf proportions, not an illustration.

### banyan-bark

Use case: photorealistic-natural. Asset type: seamless repeating albedo bark texture for a modeled Hong Kong Chinese banyan tree trunk and aerial roots. Square photographic surface scan of weathered grey-brown banyan bark, a roughly one-metre wide patch. Fine shallow vertical fissures, subtle sinuous vertical root-like ridges, muted grey and taupe tones, small pale lichen flecks and softly worn patches. Banyan bark is relatively smooth, not chunky pine bark. Perfectly straight-on orthographic flat surface, uniformly lit diffuse daylight, no deep shadows, no glare. Repeat seamlessly horizontally and vertically, no distinctive focal knot, no curved trunk silhouette, no leaves, no background, no text or borders. Photographic realistic albedo, not painted art.

### park-ground

Use case: photorealistic-natural. Asset type: seamless repeating albedo ground texture for a Hong Kong urban park in a 3D bus driving simulator. Square overhead photographic scan of a two by two metre patch of slightly worn subtropical lawn. Short fine medium olive-green grass blades with varied growth direction, occasional tiny brown fallen banyan leaves, small irregular patches of dark earthy soil showing between grass. Restrained natural variation, not a uniformly perfect carpet, not a dry brown field. Flat orthographic top-down view, diffuse cloudy daylight, even exposure and sharp detail throughout. Seamless repeating on all four edges, no large distinctive patch, no tall plants, no flowers, no rocks, no pavement, no objects, no directional shadows, no text or border. Real photographic material, not an illustration.


## Verification

The C# build passed with zero warnings and errors. The complete 1.08 km driving check passed all three stops with 26 passengers and no route contacts. The first headless run emitted an intermittent resource warning at shutdown; the verbose follow-up exited cleanly. Both logs are retained in `evidence/`, with `self-test.log` containing the final run. The final five-view capture also exited cleanly.


## Island street details — 20 September 2026

The island expansion adds a Blender-modeled news kiosk and compact street-tree variant, using the generated kiosk display and existing bark/foliage textures. Runtime placement includes 18 kiosks, 122 trees, 170 lamp posts and 64 posed pedestrians, plus street-name boards and promenade furniture. [Exact prompt, files and verification](ISLAND_EXPANSION.md#street-detail).
