shader_type spatial;
varying vec2 world_xz;
void vertex() { world_xz=(MODEL_MATRIX*vec4(VERTEX,1.0)).xz; }
void fragment() {
    vec2 p=world_xz;
    float a=sin(p.x*0.8+p.y*0.45+TIME*0.8+sin(p.y*0.17));
    float b=cos(p.y*1.1-p.x*0.3+TIME*0.55+cos(p.x*0.21));
    // Fade subpixel ripples before they form moire across the distant harbour.
    float fade=1.0-smoothstep(0.4,2.5,length(fwidth(p)));
    NORMAL_MAP=vec3(0.5+a*0.055*fade,0.5+b*0.055*fade,1.0);
    NORMAL_MAP_DEPTH=0.4;
    ALBEDO=vec3(0.025,0.105,0.12);
    ROUGHNESS=0.48;
    SPECULAR=0.25;
}
