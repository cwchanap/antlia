shader_type spatial;
render_mode shadows_disabled;
uniform sampler2D district_mask : filter_linear, repeat_disable;
uniform vec2 map_origin;
uniform vec2 map_size;
varying vec2 world_xz;
void vertex() { world_xz = (MODEL_MATRIX * vec4(VERTEX,1.0)).xz; }
void fragment() {
    vec2 uv=(world_xz-map_origin)/map_size;
    if (all(greaterThanEqual(uv,vec2(0.0))) && all(lessThanEqual(uv,vec2(1.0))) && texture(district_mask,uv).r>0.05) discard;
    ALBEDO=vec3(0.78,0.76,0.66);
    ROUGHNESS=0.95;
}
