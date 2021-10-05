from xml.etree import ElementTree as ET
import numpy, zipfile, io, random
from PIL import Image

from . import util, shared, classes
from .util import get, print, _print, print_error, print_warning
from .classes import Vec2

class KRABase:
	def __init__(self):
		self.layers = []
	
	def layers_recursive(self):
		out = []
		for l in self.layers:
			out.append(l)
			out.extend(l.layers_recursive())
		return out

class KRARoot(KRABase):
	def __init__(self, filepath):
		self.filepath = filepath
		
		with zipfile.ZipFile(filepath, "r") as kra_file:
			maindoc = kra_file.open("maindoc.xml")
			root = ET.parse(maindoc).getroot()
			
			IMAGE = root.find("{http://www.calligra.org/DTD/krita}IMAGE")
			self.name = IMAGE.attrib["name"]
			self.width = int(IMAGE.attrib["width"])
			self.height = int(IMAGE.attrib["height"])
			
			layers = IMAGE.find("{http://www.calligra.org/DTD/krita}layers")
			self.layers = [KRALayer(x, self, None) for x in layers]

class KRALayer(KRABase):
	def __init__(self, data, root, parent):
		self.root = root
		self.parent = parent
		self.layers = []
		self.x, self.y = int(data.attrib["x"]), int(data.attrib["y"])
		self.width, self.height = 1, 1
		self.tile_min_x, self.tile_min_y = 0, 0
		self.name = data.attrib["name"]
		self.nodetype = data.attrib["nodetype"]
		self.visible = data.attrib["visible"] == "1"
		self.opacity = float(data.attrib["opacity"]) / 255.0
		self.blend_mode = data.attrib["compositeop"]
		self.filename = data.attrib["filename"]
		self.bbox = (self.x,self.y,self.x+1,self.y+1)
		self.imagedata = None
		
		if data.attrib and data.attrib["nodetype"] == "grouplayer":
			for layer in data:
				self.layers = [KRALayer(x, root, self) for x in layer]
	
	def get_bounds(self):
		image = self.get_image_data()
		if not image:
			return (0, 0, 1, 1)
		minx = self.x + self.tile_min_x
		miny = self.y + self.tile_min_y
		
		bounds =  (minx, miny, minx+self.width, miny+self.height)
		_print(bounds)
		return bounds
		
	def get_image_data(self):
		if self.nodetype == "grouplayer":
			return None
		
		if self.imagedata:
			return self.imagedata
		
		with zipfile.ZipFile(self.root.filepath, "r") as kra_file:
			f = kra_file.read(f"{self.root.name}/layers/" + self.filename)
			f = io.BytesIO(f)
			
			version = int(f.readline().decode("ascii").strip().split(" ")[1])
			w = int(f.readline().decode("ascii").strip().split(" ")[1])
			h = int(f.readline().decode("ascii").strip().split(" ")[1])
			pixel_size = int(f.readline().decode("ascii").strip().split(" ")[1])
			tile_count = int(f.readline().decode("ascii").strip().split(" ")[1])
			
			if tile_count == 0:
				self.imagedata = Image.fromarray(numpy.zeros((1,1,4), dtype=numpy.uint8), "RGBA")
				return self.imagedata
			
			image_size = (w, h)
			uncompressed_size = w * h * pixel_size + 1
			step = uncompressed_size // 4
			off_g = step
			off_r = step * 2
			off_a = step * 3
			
			tiles = []
			minx = 999999
			miny = 999999
			maxx = -999999
			maxy = -999999
			
			for i in range(tile_count):
				line = f.readline().decode("ascii").strip()
				
				if line == "":
					break
				
				x, y, compression, compressed_size = line.split(",")
				x = int(x)
				y = int(y)
				minx = min(x, minx)
				miny = min(y, miny)
				maxx = max(x+w, maxx)
				maxy = max(y+h, maxy)
				
				compressed_size = int(compressed_size)-1
				compressed = f.read(1) # TODO
				tile_bytes = f.read(compressed_size)
				new_bytes = bytearray([0 for x in range(uncompressed_size)])
				lzf_decompress(tile_bytes, new_bytes)
				tile_bytes = new_bytes
				
				tiles.append((x, y, tile_bytes))
			
			imgw = maxx - minx
			imgh = maxy - miny
			
			clrs = numpy.zeros((imgh,imgw,4), dtype=numpy.uint8)
			
			for x, y, tile_bytes in tiles:
				for xx in range(w):
					for yy in range(h):
						i = xx + yy * h
						xxx = x - minx + xx
						yyy = y - miny + yy
						clrs[yyy,xxx,0] = tile_bytes[i+off_r]
						clrs[yyy,xxx,1] = tile_bytes[i+off_g]
						clrs[yyy,xxx,2] = tile_bytes[i]
						clrs[yyy,xxx,3] = tile_bytes[i+off_a]
			
			image = Image.fromarray(clrs, "RGBA")
			bbox = image.getbbox()
			self.imagedata = image.crop(bbox)
			self.tile_min_x = minx
			self.tile_min_y = miny
			self.width = bbox[2]-bbox[0]
			self.height = bbox[3]-bbox[1]
			return self.imagedata

# https://programtalk.com/python-examples/lzf.decompress/
# https://github.com/2shady4u/godot-kra-psd-importer/blob/525f433605545a964419934185a98fe865195f11/docs/KRA_FORMAT.md
# https://github.com/korlibs/korim/commit/d05eff45d0cb156336cf8dd9557731a3ec9243cb#diff-2700b714f88b93eee5490e6c92b54a7f37ec835249e1262a477e5eeaf93469e1
def lzf_decompress(indata, outdata):
	iidx = 0
	oidx = 0
	in_len = len(indata)
	
	while iidx < in_len:
		ctrl = indata[iidx]
		iidx += 1
		
		if ctrl < 32:
			for i in range(0, ctrl+1):
				outdata[oidx] = indata[iidx]
				oidx += 1
				iidx += 1
		else:
			lenn = ctrl >> 5
			if lenn == 7:
				lenn += indata[iidx]
				iidx += 1
			
			ref = oidx - ((ctrl & 0x1f) << 8) - indata[iidx] - 1
			iidx += 1
			
			for i in range(0, lenn+2):
				outdata[oidx] = outdata[ref]
				oidx += 1
				ref += 1


def process(path, data:dict):
	file = KRARoot(path)
	wide, high = file.width, file.height
	settings = shared.get_settings(data)
	
	# layers can be referenced in order
	layers = file.layers_recursive()
	
	for l in layers:
		l._name = l.name
		l._is_group = l.nodetype == "grouplayer"
		l._parent_layer = None if l.parent == None else l.parent
		
		l._bounds = l.get_bounds()
		
		l._visible = l.visible
		l._opacity = l.opacity
		l._blend_mode = l.blend_mode
		
		l.visible = True
		l.opacity = 1.0
		
		if l._is_group:
			l._layers = [x for x in l.layers]
	
	shared.update_path(layers, data)
	shared.update_child_tags(layers)
	shared.determine_drawable(layers)
	
	shared.update_area(layers, wide, high, get(settings, "padding"))
	main_origin = Vec2(wide, high) * Vec2(0, 0)
	shared.update_origins(layers, main_origin)
	main_origin = shared.localize_area(layers, main_origin)
	
	shared.save_layers_images(layers, data, lambda l: l.get_image_data())
	
	data["size"] = Vec2(wide, high)
	data["root"] = {
		"layers": shared.serialize_layers([l for l in file.layers if not l._ignore_layer])
	}