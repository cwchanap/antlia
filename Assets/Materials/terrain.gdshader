shader_type spatial;

uniform sampler2D surface_mask : filter_linear_mipmap, repeat_disable;
uniform sampler2D harbour_mask : filter_linear_mipmap, repeat_disable;
uniform vec2 harbour_origin;
uniform vec2 harbour_size;
uniform sampler2D recreation_mask : filter_linear_mipmap, repeat_disable;
uniform sampler2D sparse_recreation_atlas : filter_linear, repeat_disable;
uniform sampler2D sparse_recreation_lookup : filter_nearest, repeat_disable;
uniform sampler2D sparse_recreation_lod_ramp : filter_linear_mipmap, repeat_disable;
uniform vec2 recreation_origin;
uniform vec2 recreation_size;
uniform vec2 sparse_recreation_size;
uniform vec2 sparse_recreation_atlas_size;
uniform vec2 sparse_recreation_lookup_size;
uniform int sparse_recreation_page_columns;
uniform int sparse_recreation_mip_count = 14;
uniform vec4 sparse_recreation_mips[14];
uniform bool sparse_recreation_enabled = false;
uniform int sparse_recreation_check_mode = 0;
uniform float sparse_recreation_forced_lod = -1.0;
uniform float sparse_recreation_error_threshold = 0.00001525902;
// Authored rectangle: centre XZ, half-width/half-length; independent of map texel size.
uniform vec4 play_area;
uniform vec2 play_forward;
uniform sampler2D asphalt : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D paving : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec2 map_origin;
uniform vec2 map_size;
uniform vec3 ground_color : source_color = vec3(0.42, 0.45, 0.42);
varying vec2 world_xz;

vec3 sparse_recreation_level(vec2 uv, int level) {
    vec4 info = sparse_recreation_mips[level];
    ivec2 size = ivec2(info.xy);
    ivec2 grid = (size + ivec2(127)) / 128;
    vec2 pixel = uv * vec2(size);
    ivec2 page = clamp(ivec2(floor(pixel / 128.0)),ivec2(0),grid-ivec2(1));
    vec2 local = pixel - vec2(page * 128);
    ivec2 lookup_pixel = ivec2(page.x,int(info.z)+page.y);
    vec2 lookup_uv = (vec2(lookup_pixel)+vec2(0.5))/sparse_recreation_lookup_size;
    vec2 encoded = texture(sparse_recreation_lookup,lookup_uv).rg;
    int id = int(round(encoded.r*255.0)) + int(round(encoded.g*255.0))*256;
    if (id == 0) return vec3(0.0);
    ivec2 atlas_page = ivec2(id % sparse_recreation_page_columns,id / sparse_recreation_page_columns);
    vec2 atlas_uv = (vec2(atlas_page*130)+local+vec2(1.0))/sparse_recreation_atlas_size;
    return textureLod(sparse_recreation_atlas,atlas_uv,0.0).rgb;
}

int sparse_decode_gray(vec4 code) {
    int gray = int(code.r)+2*int(code.g)+4*int(code.b)+8*int(code.a);
    int decoded = gray^(gray>>1);
    return decoded^(decoded>>2);
}

vec4 sparse_encode_gray(int level) {
    int gray = level^(level>>1);
    return vec4(float(gray&1),float((gray>>1)&1),float((gray>>2)&1),float((gray>>3)&1));
}

float sparse_decode_lod(vec4 code) {
    int a = sparse_decode_gray(floor(code));
    int b = sparse_decode_gray(ceil(code));
    int low = min(a,b), high = max(a,b);
    return float(low)+dot(code-sparse_encode_gray(low),sparse_encode_gray(high)-sparse_encode_gray(low));
}

float sparse_recreation_lod(vec2 uv) {
    vec2 scale = sparse_recreation_size/vec2(textureSize(sparse_recreation_lod_ramp,0));
    // Constant mip colors let the original implicit filtering path select the blend.
    return sparse_decode_lod(texture(sparse_recreation_lod_ramp,uv*scale));
}

vec3 sample_sparse_recreation(vec2 uv, float lod) {
    float level = clamp(lod,0.0,float(sparse_recreation_mip_count-1));
    int low = int(floor(level));
    int high = min(low+1,sparse_recreation_mip_count-1);
    vec3 first = sparse_recreation_level(uv,low);
    float weight = fract(level);
    if (weight == 0.0) return first;
    return mix(first,sparse_recreation_level(uv,high),weight);
}

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
    vec2 ruv = (world_xz-recreation_origin)/recreation_size;
    ruv = clamp(ruv,vec2(0.0),vec2(1.0));
    float recreation_lod = sparse_recreation_forced_lod>=0.0?sparse_decode_lod(textureLod(sparse_recreation_lod_ramp,vec2(0.5),sparse_recreation_forced_lod)):
        (sparse_recreation_enabled || sparse_recreation_check_mode!=0?sparse_recreation_lod(ruv):0.0);
    vec3 dense_recreation = sparse_recreation_forced_lod>=0.0?textureLod(recreation_mask,ruv,sparse_recreation_forced_lod).rgb:texture(recreation_mask,ruv).rgb;
    vec3 recreation = sparse_recreation_enabled?sample_sparse_recreation(ruv,recreation_lod):dense_recreation;
    if (any(lessThan((world_xz-recreation_origin)/recreation_size,vec2(0.0))) || any(greaterThan((world_xz-recreation_origin)/recreation_size,vec2(1.0)))) recreation=vec3(0.0);
    if (sparse_recreation_check_mode==1) {
        ALBEDO = recreation; EMISSION = recreation; ROUGHNESS = 1.0; SPECULAR = 0.0;
    }
    else if (sparse_recreation_check_mode==2) {
        vec3 sparse = sample_sparse_recreation(ruv,recreation_lod);
        float delta = max(max(abs(dense_recreation.r-sparse.r),abs(dense_recreation.g-sparse.g)),abs(dense_recreation.b-sparse.b));
        vec3 diagnostic = vec3(step(sparse_recreation_error_threshold,delta),min(delta*255.0,1.0),0.0);
        ALBEDO = diagnostic; EMISSION = diagnostic; ROUGHNESS = 1.0; SPECULAR = 0.0;
    }
    else {
    vec3 grain = texture(asphalt,surface_uv).rgb;
    color = mix(color,turf*vec3(0.75,1.05,0.7),recreation.r);
    color = mix(color,mix(vec3(0.12,0.32,0.27),grain,0.22),recreation.g);
    color = mix(color,mix(vec3(0.42,0.16,0.10),grain,0.22),recreation.b);
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
    // Preserve the small play pad over conservatively expanded paving. Asphalt still wins.
    vec2 delta = world_xz - play_area.xy;
    vec2 edge = abs(vec2(dot(delta,vec2(play_forward.y,-play_forward.x)),dot(delta,play_forward))) - play_area.zw;
    float distance_to_play = max(edge.x,edge.y);
    float feather = max(fwidth(distance_to_play),0.01);
    float play = 1.0 - smoothstep(-feather,feather,distance_to_play);
    color = mix(color,mix(vec3(0.42,0.16,0.10),grain,0.22),play);
    ALBEDO = mix(color, texture(asphalt, surface_uv).rgb, masks.r);
    ROUGHNESS = 0.96;
    SPECULAR = 0.15;
    }
}
