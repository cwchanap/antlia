shader_type spatial;

uniform sampler2D surface_mask : filter_linear_mipmap, repeat_disable;
uniform sampler2D harbour_mask : filter_linear_mipmap, repeat_disable;
uniform vec2 harbour_origin;
uniform vec2 harbour_size;
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

vec3 coverage(vec2 p) {
    vec2 uv = (p - map_origin) / map_size;
    vec3 city = texture(surface_mask, clamp(uv,vec2(0.0),vec2(1.0))).rgb;
    if (any(lessThan(uv,vec2(0.0))) || any(greaterThan(uv,vec2(1.0)))) city=vec3(0.0);
    vec2 huv = (p-harbour_origin)/harbour_size;
    vec3 harbour = texture(harbour_mask,clamp(huv,vec2(0.0),vec2(1.0))).rgb;
    if (any(lessThan(huv,vec2(0.0))) || any(greaterThan(huv,vec2(1.0)))) harbour=vec3(0.0);
    return max(city,harbour);
}

void fragment() {
    vec3 masks = coverage(world_xz);
    vec2 surface_uv = world_xz / 2.0;
    vec3 turf = texture(grass, surface_uv).rgb;
    vec3 color = mix(mix(ground_color,turf,0.38), turf, masks.b);
    color = mix(color, texture(paving, surface_uv).rgb, masks.g);
    // Follow the union of all roads: edging cannot run across an adjoining carriageway.
    vec3 a = coverage(world_xz + vec2(0.45, 0.0));
    vec3 b = coverage(world_xz - vec2(0.45, 0.0));
    vec3 c = coverage(world_xz + vec2(0.0, 0.45));
    vec3 d = coverage(world_xz - vec2(0.0, 0.45));
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
