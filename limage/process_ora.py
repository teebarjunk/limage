from pyora import Project, TYPE_LAYER, TYPE_GROUP
from PIL import Image


from . import util, shared, classes
from .util import get, print, print_error, print_warning
from .classes import Vec2

def process(path, data:dict):
	file = Project.load(path)
	wide, high = file.dimensions
	layers = [x for x in file.children_recursive]
	root_layers = [l for l in file.children]
	
	for l in layers:
		l._name = l.name
		l._is_group = l.type == TYPE_GROUP
		l._is_clone = False # TODO: 
		l._parent_layer = None if l.parent.parent == None else l.parent
		
		l._bounds = l.get_image_data(False).getbbox()
		l._visible = l.visible
		l._opacity = l.opacity
		l._blend_mode = BLEND_MODES[l.composite_op]
		
		l.visible = True
		l.opacity = 1.0
		
		if l._is_group:
			l._layers = [x for x in l.children]
	
	def get_image(l):
		img = l.get_image_data(False)
		img = img.crop(l._bounds)
		return img
	
	shared.finalize(layers, root_layers, data, wide, high, get_image)
	
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
