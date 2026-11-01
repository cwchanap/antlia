@tool
extends EditorScenePostImport

const TEXTURES_BY_MATERIAL := {
	"Antila_banyan bark": "banyan-bark",
	"Antila_banyan leaf cutout": "banyan-leaves",
	"Antila_tactile_ochre": "pavement-stone",
	"CHT_exterior_stone": "pavement-stone",
	"CHT_asphalt": "asphalt",
}
const REQUIRED_MATERIALS := {
	"banyan": ["Antila_banyan bark", "Antila_banyan leaf cutout"],
	"street-tree": ["Antila_banyan bark", "Antila_banyan leaf cutout"],
	"planter": ["Antila_banyan leaf cutout"],
	"tactile-paver": ["Antila_tactile_ochre"],
	"cross-harbour": ["CHT_exterior_stone", "CHT_asphalt"],
}

func _post_import(scene: Node) -> Object:
	var source_name := get_source_file().get_file().get_basename()
	if not REQUIRED_MATERIALS.has(source_name):
		push_error("Unexpected shared-texture import source: " + source_name)
		return null

	var remapped := {}
	var nodes := scene.find_children("*", "MeshInstance3D", true, false)
	if scene is MeshInstance3D:
		nodes.push_front(scene)
	for node in nodes:
		var mesh_instance := node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		for surface in mesh_instance.mesh.get_surface_count():
			var material := mesh_instance.mesh.surface_get_material(surface) as StandardMaterial3D
			if material == null:
				continue
			for prefix in TEXTURES_BY_MATERIAL:
				if not material.resource_name.begins_with(prefix):
					continue
				var texture_path := "res://Assets/Textures/%s.png" % TEXTURES_BY_MATERIAL[prefix]
				var texture := load(texture_path) as Texture2D
				if material.albedo_texture == null or texture == null or texture.resource_path != texture_path:
					push_error("Invalid shared texture dependency for %s: %s" % [material.resource_name, texture_path])
					return null
				material.albedo_texture = texture
				remapped[prefix] = true
				break

	for prefix in REQUIRED_MATERIALS[source_name]:
		if not remapped.has(prefix):
			push_error("Missing shared-texture material %s in %s" % [prefix, source_name])
			return null
	print("ANTILA_SHARED_TEXTURE_REMAP_OK: ", source_name)
	return scene
