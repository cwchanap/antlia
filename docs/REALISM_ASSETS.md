# Photographic surface assets

Generated with the **built-in imagegen tool** on 12 September 2026. These are original generated albedo images, not photographs of actual premises. No external image libraries or new runtime dependencies are required.

| File in Assets/Textures | Saved resolution | Application |
| --- | --- | --- |
| weathered-tiles.png | 1254 × 1254 | Blender building walls and parapets; repeated every 2 metres in model coordinates |
| cafe-storefront.png | 2172 × 724 | Front-facing cafe windows/doors on the three shop models |
| asphalt.png | 1254 × 1254 | Main road and side streets; shared world-coordinate UVs, 2-metre repeat |
| paving.png | 1254 × 1254 | Footpaths; 2-metre repeat |

The Blender file packs the wall and shopfront images, and the GLBs embed them. The road images are loaded from the project by Godot. Mipmaps and anisotropic filtering keep the road textures readable at shallow viewing angles. The original scene view is retained in `evidence/chase-before-textures.png`; updated views use the normal capture filenames.

The saved image sizes above are the actual tool outputs; the prompts below retain their originally requested sizes. Building height variation also scales wall tiles vertically. These are albedo-only materials; surface relief remains in the mesh geometry.

Texture import files explicitly enable mipmaps because these images are assigned by C# at runtime. See Godot's [texture importer documentation](https://docs.godotengine.org/en/stable/classes/class_resourceimportertexture.html#class-resourceimportertexture-property-mipmaps-generate). The texture pass also reduces sun and ambient intensity to preserve facade detail. The final chase, cab, park-stop and bus/shelter captures were visually inspected in Godot on 12 September 2026.

## Exact generation prompts

### Weathered tiles

Use case: photorealistic-natural. Asset type: seamless repeating albedo texture for walls of Hong Kong buildings in a 3D bus simulator. Create a square 2048x2048 photographic material scan of an aged pale warm-grey ceramic mosaic exterior wall. Small square ceramic tiles, about 10 cm, straight horizontal and vertical grout lines, subtle varied off-white ivory and grey tiles, fine irregular hairline cracks, realistic dirty grey grout, delicate vertical rain streaks and patchy urban soot, occasional tiny chips. A 2 by 2 metre patch of wall viewed exactly head-on, completely flat orthographic, crisply focused throughout, soft even overcast illumination, no directional shadow, no highlight hotspot. The surface must repeat seamlessly on all four edges. Restrained surface variation without any large unique focal stain. No windows, no pipes, no fixtures, no text, no borders. Photographic physical material, not an illustration or painted artwork.

### Cafe storefront

Use case: photorealistic-natural. Asset type: front-facing Hong Kong cafe shopfront texture, applied to a 3D rectangle beneath a separate sign and canopy. Make a photorealistic 3072x1024 horizontal image, exactly 3:1. A modest lived-in Hong Kong cha chaan teng shopfront, perfectly straight-on architectural elevation, filling the image edge to edge. Three bays: brushed aluminium framed glass windows on the left and right, double glass entrance doors in the middle. Through the windows: cream tiled walls, red vinyl booth seating, stainless steel counter, warm fluorescent tubes, subtle hanging food-photo menus, stacked ceramic cups. Lower window panels have aged muted mint green and cream mosaic tiles, narrow stainless kickplates. Glass has faint reflections of opposite urban buildings and subtle fingerprints, without obscuring the interior. Fine authentic wear around frames and door handles. No people, no cars, no pavement outside, no sky, no large sign, no roof, no perspective, no logos or readable lettering, no frame. Even diffuse daylight. This is a flat architectural photographic texture, not a perspective street photo, not stylized game art.

### Asphalt

Use case: photorealistic-natural. Asset type: seamless repeating road albedo texture for a 3D Hong Kong driving game. Create a square 2048x2048 ultra-realistic material scan of worn dark neutral charcoal asphalt. A 2 metre by 2 metre patch, viewed perfectly vertically downward with orthographic projection. Fine crushed aggregate, tiny grey granite specks set in dark binder, subtle tyre-polished areas, a few thin low contrast hairline cracks and natural dust variation. Smooth drivable city road, not gravel. Dry, nonreflective, neutral colour, uniformly lit in diffuse cloudy daylight with no cast shadows. Seamless on all four edges, consistent small texture scale, no conspicuous repeating patch. No road markings, no yellow or white paint, no manholes, no kerbs, no objects, no water puddles, no leaves, no border, no text. Photographic albedo surface, not an illustration.

### Paving

Use case: photorealistic-natural. Asset type: seamless repeating pedestrian pavement albedo texture for a realistic Hong Kong street game. Create a 2048x2048 square photographic material scan of weathered rectangular concrete paving bricks in a herringbone pattern. Muted reddish terracotta and warm grey pavers, natural fine concrete pores, dusty edges, worn corners, dark thin sand-filled joints. A 2 metre by 2 metre square patch. Orthographic camera looking straight down, no perspective. Perfectly even soft overcast light, no directional shadows, no glare. Seamless repeating edges in both directions. Coherent accurate rectangular bricks and regular pattern, restrained surface wear. No kerbs, no grass, no drain covers, no road paint, no litter, no people, no text, no border. Photorealistic scanned surface, not stylized or painted.
