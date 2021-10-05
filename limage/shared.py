import sys
from pathlib import Path

import PIL
from PIL import Image
from PIL import features

from . import util, file, classes
from .classes import Vec2
from .util import get, print, print_error, print_warning

DEFAULT_SETTINGS:dict = {
	"sep": "-",				# change to "/" to folderize
	
	# texture related
	"scale": 1,						# rescale textures
	"origin": [.5, .5],				# multiplied by size of texture
	
	"padding": 1,
	
	# can really decrease file size, but at cost of color range.
	# https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.quantize
	"quantize": False,				# decrease size + decrease quality
	
	# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
	# https://docs.godotengine.org/en/stable/getting_started/workflow/assets/importing_images.html
	"format": "PNG",
	
	"PNG": {
		"optimize": True,
	},
	
	"WEBP": {
		"lossless": True,
		"method": 3,
		"quality": 80
	},

	"JPEG": {
		"optimize": True,
		"quality": 80
	}
}

COMPLAINED_ABOUT_WEBP:bool = False

def get_settings(data):
	settings = data["settings"]
	
	if not "output" in settings: settings["output"] = util.ARGS.output
	if not "format" in settings: settings["format"] = util.ARGS.format
	if not "padding" in settings: settings["padding"] = util.ARGS.padding
	if not "quantize" in settings: settings["quantize"] = util.ARGS.quant
	if not "sep" in settings: settings["sep"] = util.ARGS.sep
	
	return util.merge_unique(settings, DEFAULT_SETTINGS)

def get_layer_path(l) -> list:
	path = []
	full_path = [l._name]
	while l._parent_layer:
		path.insert(0, l._parent_layer._name)
		full_path.insert(0, l._parent_layer._name)
		l = l._parent_layer
	return path, full_path

def get_layer_by_path(layers, path):
	path = path.split("/")
	for l in layers:
		if l._full_path == path:
			return l
	return None

def get_all_descendants(l, out):
	for c in l._layers:
		out.append(c)
		if hasattr(c, "_layers"):
			get_all_descendants(c, out)
	return out

def update_path(layers, data):
	# directory = Path(data["directory"]) / data["name"]
	
	lindex = 0
	for l in layers:
		l._name, l._tags, l._layer_tags, l._deep_layer_tags = util.parse_name(l._name)
		if l._name.strip() == "":
			l._name = f"UNNAMED{lindex}"
		l._index = lindex
		lindex += 1
		
		if hasattr(l, "_layers"):
			l._deep_layers = get_all_descendants(l, [])
			# print("===\n",
			# 	[x._name for x in l._layers],
			# 	[x._name for x in l._deep_layers])
	
	settings = data["settings"]
	texture_seperator = settings["sep"]
	texture_format = settings["format"]
	texture_extension = get(settings, "extension", texture_format.lower())
	
	for l in layers:
		l._path, l._full_path = get_layer_path(l)
		
		file_name = texture_seperator.join(l._full_path) + f".{texture_extension}"
		l._texture = file_name
		l._texture_dir = util.ARGS.output
		l._texture_scale = 1

def update_child_tags(layers):
	# apply tags to children
	for l in layers:
		if l._is_group:
			
			if "merge" in l._tags:
				l._is_group = False
			
			if "options" in l._tags:
				for c in l._layers:
					c._tags["option"] = l._name
			
			if "toggles" in l._tags:
				for c in l._layers:
					c._tags["toggle"] = l._name
			
			# add child tags
			if len(l._layer_tags):
				for c in l._layers:
					for tag in l._layer_tags:
						if not tag in c._tags:
							c._tags[tag] = l._tags[tag]
			
			# add descendant tags
			if len(l._deep_layer_tags):
				for c in l._deep_layers:
					for tag in l._deep_layer_tags:
						if not tag in c._tags:
							c._tags[tag] = l._tags[tag]
		
		del l._layer_tags
		del l._deep_layer_tags

def print_names(l):
	print([x._name for x in l])

def determine_drawable(layers):
	for l in layers:
		l._ignore_layer = False
		l._export_image = True
	
	for l in layers:
		if l._is_group:
			l._export_image = False
		
		# don't export image.
		for k in ["x", "copy", "origin", "point"]:
			if k in l._tags:
				l._ignore_layer = True
				l._export_image = False
		
		# don't export children.
		for k in ["merge", "origins"]:
			if k in l._tags:
				l._ignore_layer = True
				l._export_image = False
				# print("===\n", l._name)
				# print_names(l._layers)
				# print_names(l._deep_layers)
				for d in l._deep_layers:
					d._ignore_layer = True
					d._export_image = False
		
		# ignore layers.
		for k in ["x", "origin", "point"]:
			if k in l._tags:
				l._ignore_layer = True
				l._export_image = False
				if hasattr(l, "_deep_layers"):
					for d in l._deep_layers:
						d._ignore_layer = True
						d._export_image = False

def update_area(layers, max_wide:int, max_high:int, padding:int=1):
	for l in layers:
		x, y, r, b = l._bounds
		x -= padding
		y -= padding
		r += padding
		b += padding
		
		x, y, r, b = max(x, 0), max(y, 0), min(r, max_wide), min(b, max_high)
		
		w = r - x
		h = b - y
		
		l._bounds_top = Vec2(x, y)
		l._bounds_size = Vec2(w, h)
		l._position = Vec2(x, y)
		l._origin = Vec2(x, y) + l._bounds_size * .5
		l._bbox = (x, y, r, b)

def update_origins(layers, main_origin):
	# update origins
	for l in layers:
		if "point" in l._tags:
			pass
		
		if "origin" in l._tags:
			if not l._parent_layer:
				main_origin = l._origin
			else:
				l.parent._origin = l._origin
		
		if "origins" in l._tags:
			for c in l._layers:
				target = get_layer_by_path(layers, c._name)
				target._origin = c._origin
	
	return main_origin

def localize_area(layers, psd_origin):
	for l in layers:
		# center on main origin
		l._position -= psd_origin
		l._origin -= psd_origin
		
		# 'copy' origin
		if "copy" in l._tags:
			dif = l._copy_from._origin - l._copy_from._position
			l._origin = l._position + dif
	
	# localize points
	for l in layers:
		p = l._parent_layer
		while p != None:
			l._position -= p._position
			l._origin -= p._position
			p = p._parent_layer
	
	# center
	for l in layers:
		l._position += l._bounds_size * .5
		l._origin -= l._position
		
		l._position += l._origin
		l._origin += l._bounds_size * .5
	
	# def localize_to_parent(parent, child):
	# 	if parent:
	# 		child._out_position -= parent._out_origin
	
	# localize to parent
	for l in layers:
		if l._parent_layer:
			l._position -= l._parent_layer._origin
	
	# on_descendants(None, output, localize_to_parent)

def serialize_layers(layers:list):
	out = []
	for l in layers:
		if not l._ignore_layer:
			out.append(serialize_layer(l))
	out.reverse() # reverse layers since most programs render top to bottom.
	return out

def serialize_layer(l) -> dict:
	out = {
		"name": l._name,
		"path": l._path,
		"full_path": l._full_path,
		"tags": l._tags,
		"visible": l._visible,
		"opacity": l._opacity,
		"blend_mode": l._blend_mode,
		"position": l._position,
		"origin": l._origin,
		"area": {
			"x": l._bounds_top.x,
			"y": l._bounds_top.y,
			"w": l._bounds_size.x,
			"h": l._bounds_size.y
		}
	}
	
	if hasattr(l, "_texture") and l._export_image:
		out["texture"] = str(l._texture)
		out["directory"] = str(l._texture_dir)
		out["scale"] = l._texture_scale
	
	if hasattr(l, "_points"):
		out["points"] = l._points
	
	if l._is_group:
		out["layers"] = serialize_layers(l._layers)
	
	return out


def save_layers_images(layers, data, image_getter):
	if util.ARGS.skip_images:
		return
	
	for l in layers:
		if not l._ignore_layer and l._export_image and hasattr(l, "_texture"):
			image = image_getter(l)
			_save_layer_image(image, l, data)

def _save_layer_image(image, l, data):
	global COMPLAINED_ABOUT_WEBP
	
	settings = data["settings"]
	
	texture_format = settings["format"]
	texture_format_settings = get(settings, texture_format, {})
	texture_extension = get(settings, "extension", texture_format.lower())
	
	# webp warning
	if texture_format == "WEBP" and not COMPLAINED_ABOUT_WEBP:
		webp_supported:bool = features.check_module('webp')
		if not webp_supported:
			COMPLAINED_ABOUT_WEBP = True
			print(f"PILLOW v{PIL.__version__}")
			print(f"WEBP support: {WEBP_SUPPORTED}")
			print(f"  libwebp library might not be installed")
			print(f"  Ubuntu: sudo apt-get install -y libwebp-dev")
	
	# image processing
	tags = l._tags
	is_mask = "mask" in tags
	scale = get(tags, "scale", get(settings, "scale", 1))
	
	# Scale.
	if scale != 1:
		w, h = image.size
		w = math.ceil(w * scale)
		h = math.ceil(h * scale)
		image = image.resize((w, h), Image.NEAREST if is_mask else Image.LANCZOS)
	
	# Optional: Quantize (Can really reduce size, but at cost of colors.)
	# 0 = median cut 1 = maximum coverage 2 = fast octree
	if is_mask:
		image = image.quantize(colors=2, method=2, dither=Image.NONE)
	
	elif get(settings, "quantize", False):#self.get_settings("quantize"):
		image = image.quantize(method=3)
	
	# generate polygon
	# TODO: move this somewhere else
	if "poly" in l._tags:
		import genpoly
		poly_path = self.data_path(f"poly_{l.name}", "tscn")
		points = genpoly.get_points(image, l._texture)
		save_string(poly_path, points)
	
	# RGBA -> RGB
	if texture_format in ["JPEG"]:
		new_image = Image.new("RGB", image.size, (255, 255, 255))
		new_image.paste(image, mask=image.split()[3])
		image = new_image
	
	path = Path(l._texture_dir) / l._texture
	file.make_dir(path.parent)
	image.save(path, texture_format, **texture_format_settings)
	
	print(f"saved: {path}")