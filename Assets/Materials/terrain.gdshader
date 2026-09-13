shader_type spatial;

uniform sampler2D surface_mask : filter_linear_mipmap, repeat_disable;
uniform sampler2D asphalt : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D paving : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec2 map_origin;
uniform vec2 map_size;
uniform vec3 ground_color : source_color = vec3(0.42, 0.45, 0.42);
varying vec2 world_xz;

void vertex() {
    world_xz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
    vec2 map_uv = (world_xz - map_origin) / map_size;
    vec3 masks = texture(surface_mask, map_uv).rgb;
    if (any(lessThan(map_uv, vec2(0.0))) || any(greaterThan(map_uv, vec2(1.0)))) {
        masks = vec3(0.0);
    }
    vec2 surface_uv = world_xz / 2.0;
    vec3 color = mix(ground_color, texture(grass, surface_uv).rgb, masks.b);
    color = mix(color, texture(paving, surface_uv).rgb, masks.g);
    // Follow the union of all roads: edging cannot run across an adjoining carriageway.
    vec2 offset = vec2(0.45) / map_size;
    vec3 a = texture(surface_mask, map_uv + vec2(offset.x, 0.0)).rgb;
    vec3 b = texture(surface_mask, map_uv - vec2(offset.x, 0.0)).rgb;
    vec3 c = texture(surface_mask, map_uv + vec2(0.0, offset.y)).rgb;
    vec3 d = texture(surface_mask, map_uv - vec2(0.0, offset.y)).rgb;
    // Kerbs follow asphalt and park paths, not tiny gaps between cadastral building lots.
    float grass_edge = max(max(a.b * (1.0 - a.g), b.b * (1.0 - b.g)), max(c.b * (1.0 - c.g), d.b * (1.0 - d.g)));
    float border = max(max(max(a.r, b.r), max(c.r, d.r)), grass_edge);
    float joint = min(abs(fract(world_xz.x) - 0.5), abs(fract(world_xz.y) - 0.5));
    vec3 edging = texture(stone, world_xz / 0.6).rgb * mix(0.65, 1.0, smoothstep(0.006, 0.025, joint));
    color = mix(color, edging, smoothstep(0.1, 0.9, border) * masks.g);
    ALBEDO = mix(color, texture(asphalt, surface_uv).rgb, masks.r);
    ROUGHNESS = 0.96;
    SPECULAR = 0.15;
}
