// Sharp pixel-art sampling for a moving 3D camera.
// Each texel is drawn as a crisp square, but its edges are blended across
// about one screen pixel, so pixels don't shimmer or crawl when the camera
// moves, a sprite rotates or the view scales by a non-whole amount.
shader_type spatial;
render_mode cull_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
// Ground: tile the texture in world space at its real-world size.
uniform bool world_uv = false;
uniform vec2 world_tile_m = vec2(4.0, 4.0);
uniform vec2 uv_offset = vec2(0.0);
uniform bool flip_h = false;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = world_uv ? world_pos.xz / world_tile_m : UV;
	if (flip_h) {
		uv.x = 1.0 - uv.x;
	}
	uv += uv_offset;

	vec2 size = vec2(textureSize(albedo_tex, 0));
	vec2 px = uv * size;
	vec2 edge = floor(px + 0.5);
	vec2 width = max(fwidth(px), vec2(1e-5));
	px = edge + clamp((px - edge) / width, -0.5, 0.5);
	// Mip level comes from the original UVs so distant textures still filter.
	vec4 color = textureGrad(albedo_tex, px / size, dFdx(uv), dFdy(uv));

	ALBEDO = color.rgb;
	ALPHA = color.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ALPHA_ANTIALIASING_EDGE = 0.3;
}
