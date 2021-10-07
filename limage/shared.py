import sys
from math import ceil, floor
from pathlib import Path

import PIL
from PIL import Image
from PIL import features

from . import util, file, classes
from .classes import Vec2
from .util import get, _print, print, print_error, print_warning

DEFAULT_SETTINGS:dict = {
	"seperator": "-",				# change to "/" to folderize
	
	# texture related
	"scale": 1,						# rescale textures
	"origin": [.5, .5],				# multiplied by size of texture
	
	"padding": 1,
	
	# can really decrease file size, but at cost of color range.
	# https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.quantize
	"quantize": False,				# decrease size + decrease quality
	"quantize_method": 3,
	"quantize_colors": 255,
	
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
	if not "seperator" in settings: settings["seperator"] = util.ARGS.seperator
	if not "scale" in settings: settings["scale"] = util.ARGS.scale
	
	if not "quantize" in settings:
		qenabled, qmethod, qcolors = util.ARGS.quant.split(",")
		settings["quantize"] = True if qenabled=="1" else False
		settings["quantize_method"] = int(qmethod)
		settings["quantize_colors"] = int(qcolors)
	
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

def finalize(layers, root_layers, data, width, height, get_image):
	settings = get_settings(data)
	
	update_path(layers, data)
	update_child_tags(layers)
	determine_drawable(layers)
	
	scale = get(settings, "scale")
	padding = get(settings, "padding")
	
	new_width = int(floor(width * scale))
	new_height = int(floor(height * scale))
	
	points = []
	
	update_area(layers, new_width, new_height, scale, padding)
	main_origin = Vec2(new_width, new_height) * Vec2(0, 0)
	inital_origin = main_origin
	
	main_origin = update_origins(points, layers, main_origin)
	localize_area(layers, main_origin)
	
	save_layers_images(layers, data, get_image)
	
	data["size"] = Vec2(new_width, new_height)
	data["original_size"] = Vec2(width, height)
	data["root"] = { "layers": serialize_layers([l for l in root_layers if not l._ignore_layer]) }
	
	if len(points):
		data["root"]["points"] = points
		diff = inital_origin - main_origin
		for x in points: x["position"] += diff

def update_path(layers, data):
	lindex = 0
	for l in layers:
		l._name, l._tags, l._layer_tags, l._deep_layer_tags = util.parse_name(l._name)
		
		# force a name for unnamed nodes
		if l._name.strip() == "":
			if "options" in l._tags: l._name = "options"
			elif "toggles" in l._tags: l._name = "toggles"
			elif l._tags: l._name = iter(l._tags).__next__()
			else: l._name = f"noname_{lindex}"
		
		# layer index
		l._index = lindex
		lindex += 1
		
		if hasattr(l, "_layers"):
			l._deep_layers = get_all_descendants(l, [])
	
	settings = data["settings"]
	texture_seperator = settings["seperator"]
	texture_format = settings["format"]
	texture_extension = get(settings, "extension", texture_format.lower())
	
	for l in layers:
		l._path, l._full_path = get_layer_path(l)
		
		file_name = texture_seperator.join(l._full_path) + f".{texture_extension}"
		l._texture = file_name
		l._texture_dir = util.ARGS.output
		l._texture_scale = get(settings, "scale")
		
		l._points = []

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
		l._ignore_layer = False # will layer data be exported?
		l._export_image = True # will layer image be exported?
	
	for l in layers:
		if l._is_group:
			l._export_image = False
		
		# don't export children.
		for k in ["merge", "origins", "points"]:
			if k in l._tags:
				l._ignore_layer = True
				l._export_image = False
				for d in l._deep_layers:
					d._ignore_layer = True
					d._export_image = False
		
		# ignore layers.
		for k in ["x", "copy", "origin", "point"]:
			if k in l._tags:
				l._ignore_layer = True
				l._export_image = False
				if hasattr(l, "_deep_layers"):
					for d in l._deep_layers:
						d._ignore_layer = True
						d._export_image = False

def update_area(layers, max_wide:int, max_high:int, scale:float=1.0, padding:int=1):
	for l in layers:
		x, y, r, b = l._bounds
		
		l._bbox = (x, y, r, b)
		
		x = x * scale
		y = y * scale
		r = r * scale
		b = b * scale
		
		for x in l._points: l._points *= scale
		
		# clamp to image bounds?
		if True: # TODO: Add toggle somewhere.
			x, y, r, b = max(x, 0), max(y, 0), min(r, max_wide), min(b, max_high)
		else:
			x, y, r, b = x, y, r, b
		
		x -= padding
		y -= padding
		r += padding
		b += padding
		
		w = r - x
		h = b - y
		
		l._bounds_top = Vec2(x, y)
		l._bounds_size = Vec2(w, h)
		l._position = Vec2(x, y)
		l._origin = Vec2(x, y) + l._bounds_size * .5

def update_origins(global_points, layers, main_origin):
	# update origins
	for l in layers:
		# add point to parent
		if "point" in l._tags:
			del l._tags["point"]
			point = { "name": l._name, "position": l._origin, "tags": l._tags }
			if l._parent_layer == None:
				global_points.append(point)
			else:
				l.parent._points.append(point)
		
		# add points to objects
		if "points" in l._tags:
			del l._tags["points"]
			for c in l._layers:
				target = get_layer_by_path(layers, c._name)
				if target != None:
					target._points.append({ "name": l._name, "position": c._origin, "tags": c._tags })
				else:
					_print("can't find layer " + c._name)
		
		# global origin
		if "origin" in l._tags:
			if l._parent_layer == None:
				main_origin = l._origin
			else:
				l.parent._origin = l._origin
		
		if "origins" in l._tags:
			for c in l._layers:
				target = get_layer_by_path(layers, c._name)
				target._origin = c._origin
	
	return main_origin

def localize_area(layers, main_origin):
	for l in layers:
		l._initial_position = l._origin
		
		# force group to origin
		if l._is_group:
			l._position = main_origin
			l._origin = main_origin
		
		# center on main origin
		l._position -= main_origin
		l._origin -= main_origin
		
		# TODO: Finish smart layers/clone layers
		# 'copy' origin
		# if "copy" in l._tags or l._is_clone:
		# 	dif = l._copy_from._origin - l._copy_from._position
		# 	l._origin = l._position + dif
	
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
	
	# localize to parent
	for l in layers:
		if l._parent_layer:
			l._position -= l._parent_layer._origin
	
	# move points
	for l in layers:
		diff = l._origin - l._initial_position
		diff -= l._bounds_size * .5
		for x in l._points: x["position"] += diff
	
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
	
	if len(l._points):
		out["points"] = l._points
	
	if hasattr(l, "shapes"):
		out["shapes"] = l.shapes
	
	if hasattr(l, "_texture") and l._export_image:
		out["texture"] = str(l._texture)
		out["scale"] = l._texture_scale
	
	if l._is_group:
		out["layers"] = serialize_layers(l._layers)
	
	return out


def save_layers_images(layers, data, image_getter):
	if util.ARGS.skip_images:
		return
	
	for l in layers:
		if not l._ignore_layer and l._export_image and hasattr(l, "_texture"):
			image = image_getter(l)
			if image != None:
				_save_layer_image(image, l, data)
			
			# delete texture field so it won't be added to output struct
			else:
				del l._texture

def m_eight(x):
	return ((x + 7) & (-8))

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
	scale = get(tags, "scale", get(settings, "scale"))
	padding = get(settings, "padding")
	
	# Scale.
	if scale != 1:
		w, h = image.size
		w = ceil(w * scale)
		h = ceil(h * scale)
		image = image.resize((w, h), Image.NEAREST if is_mask else Image.LANCZOS)
	
	# Padding.
	if padding != 0:
		w, h = image.size
		w += padding*2
		h += padding*2
		padded = Image.new(image.mode, (w,h), (0,0,0,0))
		padded.paste(image, (padding, padding))
		image = padded
	
	if is_mask:
		image = image.quantize(colors=2, method=2, dither=Image.NONE)
	
	# Optional: Quantize (Can really reduce size, but at cost of colors.)
	# 0 = median cut 1 = maximum coverage 2 = fast octree
	elif get(settings, "quantize", False):
		image = image.quantize(method=settings["quantize_method"], colors=settings["quantize_colors"])
	
	# generate polygon
	# TODO: move this somewhere else
	if "poly" in l._tags:
		import genpoly
		poly_path = self.data_path(f"poly_{l.name}", "tscn")
		points = genpoly.get_points(image, l._texture)
		save_string(poly_path, points)
	
	# RGBA -> RGB
	if texture_format in ["JPEG"]:
		# new_image = Image.new("RGB", image.size, (255, 255, 255))
		# new_image.paste(image, mask=image.split()[3])
		image = image.convert("RGB")
	
	elif texture_format in ["BMP"]:
		# TODO: Fix
		_, _, _, a = image.convert("RGBA").split()
		bg = Image.merge("RGB", (a, a, a))
		w, h = image.size
		image = bg.convert("1").resize((m_eight(w), m_eight(h)), Image.NEAREST)
	
	path = Path(l._texture_dir) / l._texture
	file.make_dir(path.parent)
	image.save(path, texture_format, **texture_format_settings)
	
	print(f"saved: {path}")