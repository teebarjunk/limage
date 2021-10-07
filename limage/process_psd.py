from psd_tools import PSDImage
from psd_tools.constants import Tag


from . import util, file, classes, shared
from .util import get, print, print_error, print_warning
from .classes import Vec2

def process(path, data:dict):
	psd = PSDImage.open(path)
	wide, high = psd.size
	layers = list(psd.descendants())
	root_layers = [l for l in psd]
	
	for l in layers:
		l._name = l.name
		l._is_group = l.kind == "group"
		l._is_clone = l.kind == "smartobject"
		l._parent_layer = None if l.parent == psd else l.parent
		
		l._bounds = l.bbox
		l._visible = l.visible
		l._opacity = l.opacity / 255.0
		l._blend_mode = str(l.blend_mode).split(".", 1)[1].lower()
		
		l.visible = True
		l.opacity = 255
		
		if l._is_group:
			l._layers = [x for x in l]
	
	def get_image(l):
		return l.composite(l.bbox)
	
	shared.finalize(layers, root_layers, data, wide, high, get_image)
	
	# shared.update_path(layers, data)
	# shared.update_child_tags(layers)
	# shared.determine_drawable(layers)
	
	# # get initial rect
	# shared.update_area(layers, wide, high, get(settings, "padding"))
	# main_origin = Vec2(wide, high) * Vec2(0, 0)
	# main_origin = shared.update_origins(layers, main_origin)
	# main_origin = shared.localize_area(layers, main_origin)
	
	# shared.save_layers_images(layers, data, lambda l: l.composite(l._bbox))
	
	# # output
	# data["size"] = Vec2(wide, high)
	# data["root"] = {
	# 	"layers": shared.serialize_layers([l for l in root_layers if not l._ignore_layer])
	# }