from pyora import Project, TYPE_LAYER, TYPE_GROUP
from PIL import Image

from . import util, shared, classes
from .util import get, print, print_error, print_warning
from .classes import Vec2

# normalizing blend modes
BLEND_MODES:dict = {
	"svg:src-over": "normal",
	"svg:multiply": "multiply",
	"svg:screen": "screen",
	"svg:overlay": "overlay",
	"svg:darken": "darken",
	"svg:lighten": "lighten",
	"svg:color-dodge": "dodge",
	"svg:color-burn": "burn",
	"svg:hard-light": "hard_light",
	"svg:soft-light": "soft_light",
	"svg:difference": "difference",
	"svg:color": "color",
	"svg:luminosity": "luminosity",
	"svg:hue": "hue",
	"svg:saturation": "saturation",
	"svg:plus": "plus",
	"svg:dst-in": "dst_in",
	"svg:dst-out": "dst_out",
	"svg:src-atop": "src_atop",
	"svg:dst-atop": "dst_atop",
}

def process(items:list):
	for item in items:
		process_file(item)

def process_file(data:dict):
	file = Project.load(data["path"])
	wide, high = file.dimensions
	settings = shared.get_settings(data)
	
	padding = get(settings, "padding")
	
	# layers can be referenced in order
	layers = [x for x in file.children_recursive]
	
	for l in layers:
		l.name, l._tags, l._child_tags, l._descendant_tags = util.parse_name(l.name)
		l._visible = l.visible
		l._opacity = l.opacity
		l._blend_mode = BLEND_MODES[l.composite_op]
		
		l.visible = True
		l.opacity = 1.0
		
		l._is_group = l.type == TYPE_GROUP and not "merge" in l._tags
		l._export_image = True
		l._parent_layer = None if l.parent.parent == None else l.parent
		
		if l._is_group:
			l._layers = [x for x in l.children]
			l._deep_layers = [x for x in l.children_recursive]
	
	shared.update_path(layers, data)
	shared.determine_drawable(layers)
	
	for l in layers:
		img = l.get_image_data()
		l._bounds = img.getbbox()
		
		if l._export_image:
			img = img.crop(l._bounds) 
			shared.save_layer_image(img, l, data)
	
	shared.update_area(layers, wide, high, padding)
	
	main_origin = Vec2(wide, high) * Vec2(.5, .5)
	main_origin = shared.localize_area(layers, main_origin)
	
	data["size"] = Vec2(wide, high),
	data["root"] = {
		"layers": shared.serialize_layers([l for l in file.children])
	}
	
	# util.print_json(data["root"]["layers"])

	# print(dir(layer))
	# print("")
	# if l.type == TYPE_LAYER:
		# print(dir(layer))
		# print(layer.name, layer.opacity,  layer.composite_op, layer.visible, layer.hidden)
	
	# elif layer.type == TYPE_GROUP:
		# print(layer.name)
# 		for l in layer.children:
# 			print("  ", l.name)

# for layer in project.children:
# 	if layer.type == TYPE_LAYER:
# 		img = layer.get_image_data()
# 		print(img.getbbox())
		
# 		img = img.crop(img.getbbox())
		
		
# 		img.save(f"{layer.name}.png")