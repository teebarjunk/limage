from psd_tools import PSDImage
from psd_tools.constants import Tag
# from psd_tools.constants import BlendMode
import json, sys
from pathlib import Path

from . import util, file, classes, shared
from .util import get, print, print_error, print_warning
from .classes import Vec2

__version__ = "0.3"

def process(path, item:dict):
	settings = shared.get_settings(data)
	
	psd = PSDImage.open(path)
	wide, high = psd.size
	layers = list(psd.descendants())
	
	# get name and tag data
	for l in layers:
		l._name = l.name
		l._is_group = l.kind == "group"
		l._parent_layer = None if l.parent == self.psd else l.parent
		
		l._bounds = l.bbox
		l._visible = l.visible
		l._opacity = l.opacity / 255.0
		l._blend_mode = str(l.blend_mode).split(".", 1)[1].lower()
		
		l.visible = True
		l.opacity = 255
		
		if l._is_group:
			l._layers = [x for x in l]
	
	shared.update_path(layers, data)
	shared.update_child_tags(layers)
	
	# get initial rect
	shared.update_area(layers, wide, high, get(settings, "padding"))
	shared.update_origins(layers)
	
	# psd origin
	main_origin = Vec2(wide, high) * Vec2(get(settings, "origin"))
	main_origin = shared.localize_area(layers, main_origin)
	
	shared.save_layers_images(layers, item, lambda l: l.composite(l._bbox))
	
	# output
	item["size"] = Vec2(wide, high)
	item["root"] = {
		"layers": shared.serialize_layers([l for l in psd if not l._ignore_layer])
	}