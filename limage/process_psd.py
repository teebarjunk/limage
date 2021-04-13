from psd_tools import PSDImage
from psd_tools.constants import Tag
# from psd_tools.constants import BlendMode
import json, sys
from pathlib import Path

from . import util, file, classes, shared
from .util import get, print, print_error, print_warning
from .classes import Vec2

__version__ = "0.3"

class PSDProcessor:
	
	def __init__(self, data):
		self.data = data
		
		self.settings = shared.get_settings(data)
		
		self.psd = PSDImage.open(data["path"])
		self.wide, self.high = self.psd.size
		self.layers = list(self.psd.descendants())
		
		self.update_names()
		self.update_positions()
		
		shared.save_layers_images(self.layers, self.data, lambda l: l.composite(l._clamped_bbox))
		
		# output
		self.data["size"] = Vec2(self.wide, self.high)
		self.data["root"] = {
			"layers": shared.serialize_layers([l for l in self.psd])
		}
	
	# settings
	def get_settings(self, key:str, default=None):
		if key in self.settings:
			return self.settings[key]
		if key in DEFAULT_SETTINGS:
			return DEFAULT_SETTINGS[key]
		print_warning(f"no settings key: {key}")
		return default
	
	def update_names(self):
		lindex = 0
		
		# get name and tag data
		for l in self.layers:
			l.name, l._tags, l._child_tags, l._descendant_tags = util.parse_name(l.name)
			l.name = l.name if l.name != "" else f"UNNAMED_{lindex}"
			l._index = lindex
			lindex += 1
			
			l._is_group = l.kind == "group" and not "merge" in l._tags
			l._parent_layer = None if l.parent == self.psd else l.parent
			l._bounds = l.bbox
			
			l._visible = l.visible
			l._opacity = l.opacity / 255.0
			l._blend_mode = str(l.blend_mode).split(".", 1)[1].lower()
			l._export_image = True
			
			l.visible = True
			l.opacity = 255
			
			if l._is_group:
				l._layers = [x for x in l]
				l._deep_layers = [x for x in l.descendants()]
		
		shared.update_path(self.layers, self.data)
		
		# apply tags to children
		for l in self.layers:
			if l.kind == "group":
				if len(l._child_tags):
					for child in l:
						for tag in l._child_tags:
							if not tag in child._tags:
								child._tags[tag] = l._tags[tag]
				
				if len(l._descendant_tags):
					for child in l.descendants():
						for tag in l._descendant_tags:
							if not tag in child._tags:
								child._tags[tag] = l._tags[tag]
				
				l._export_image = False
				# if "merge" in l._tags:
				# 	for child in l.descendants():
				# 		child._export_image = False
				
				# else:
				# 	l._export_image = False
			
			del l._child_tags
			del l._descendant_tags
		
		# for l in self.layers:
		# 	for t in ["x", "copy", "merge", "origins", "origin", "point"]:
		# 		if t in l._tags:
		# 			l._export_image = False
	
	def update_positions(self):
		padding = self.get_settings("padding")
		
		# get initial rect
		shared.update_area(self.layers, self.wide, self.high, padding)
		
		# update origins
		for l in self.layers:
			if "point" in l._tags:
				pass
			
			if "origin" in l._tags:
				if l.parent == self.psd:
					self.origin = l._origin
				else:
					l.parent._origin = l._origin
		
		for l in self.layers:
			if "origins" in l._tags:
				for child_origin in l.descendants():
					child = self.find_layer(self.psd, child_origin.name)
					child._origin = child_origin._origin
					# set for descendants as well
					if child.kind == "group":
						for d in child.descendants():
							d._origin = child_origin._origin
		
		# psd origin
		main_origin = Vec2(self.wide, self.high) * Vec2(self.get_settings("origin"))
		main_origin = shared.localize_area(self.layers, main_origin)
		
	
	# def update_images(self):
		# local_path = Path(self.get_settings("directory"))
		# directory = Path(self.data["directory"]) / local_path#Path(self.get_settings("texture_dir"))
		
		# texture_format = self.get_settings("format")
		# texture_extension = self.get_settings("extension", texture_format.lower())
		# texture_format_settings = dict(self.get_settings(texture_format, {}))
		
		# texture_scale = self.get_settings("scale")
		
		# copy default texture format settings
		# if texture_format in DEFAULT_SETTINGS:
		# 	for key in DEFAULT_SETTINGS[texture_format]:
		# 		if not key in texture_format_settings:
		# 			texture_format_settings[key] = DEFAULT_SETTINGS[texture_format][key]
		
		
		
		# for l in self.layers:
		# 	if not l._export_image:
		# 		continue
			
		# 	if SKIP_IMAGES:
		# 		continue
			
		# 	image = l.composite(l._clamped_bbox)
		# 	# texture_path = directory / name
		# 	file.save_layer_image(image, l, self.data)#,# texture_path, texture_format, texture_format_settings,)
			
	
	def find_layer(self, layer, child_name):
		l = layer
		for part in child_name.split("-"):
			found = False
			for c in l:
				if c.name == part:
					l = c
					found = True
					break
			if not found:
				print(f"can't find '{child_name}' in {layer.name}")
				return None
		return l
	
	def find_layer_with_name(self, name:str):
		for layer in self.all_layers:
			if layer.name == name:
				return layer
		print(f"cant find layer named '{name}'")
		return None
	
	# def get_layer_path(self, layer) -> list:
	# 	path = []
	# 	full_path = [layer.name]
	# 	while layer.parent != None and layer.parent != self.psd:
	# 		path.insert(0, layer.parent.name)
	# 		full_path.insert(0, layer.parent.name)
	# 		layer = layer.parent
	# 	return path, full_path

def process(items:list):
	for item in items:
		PSDProcessor(item)