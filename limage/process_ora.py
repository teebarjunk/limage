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

def process(path, data:dict):
	def get_image(l):
		img = l.get_image_data()
		img = img.crop(l._bounds)
		return img
	
	file = Project.load(path)
	wide, high = file.dimensions
	settings = shared.get_settings(data)
	
	# layers can be referenced in order
	layers = [x for x in file.children_recursive]
	
	for l in layers:
		l._name = l.name
		l._is_group = l.type == TYPE_GROUP
		l._parent_layer = None if l.parent.parent == None else l.parent
		
		l._bounds = l.get_image_data().getbbox()
		l._visible = l.visible
		l._opacity = l.opacity
		l._blend_mode = BLEND_MODES[l.composite_op]
		
		l.visible = True
		l.opacity = 1.0
		
		if l._is_group:
			l._layers = [x for x in l.children]
			
	shared.update_path(layers, data)
	shared.update_child_tags(layers)
	shared.determine_drawable(layers)
	
	shared.update_area(layers, wide, high, get(settings, "padding"))
	main_origin = Vec2(wide, high) * Vec2(0, 0)
	shared.update_origins(layers, main_origin)
	main_origin = shared.localize_area(layers, main_origin)
	
	shared.save_layers_images(layers, data, get_image)
	
	data["size"] = Vec2(wide, high)
	data["root"] = {
		"layers": shared.serialize_layers([l for l in file.children if not l._ignore_layer])
	}