import sys, os, json
import importlib
from pathlib import Path
from . import __info__, file, util
from .util import get, print, print_warning, print_error, EXTENSIONS

__version__ = __info__.__version__

PROCESSORS:dict = {}

def get_settings(path) -> tuple:
	for k in [".json", ".yaml"]:
		p = path.with_suffix(k)
		if p.exists():
			return p, file.time(p), file.load(p)
	return "", "", {}

def get_current_directory():
	for item in sys.argv[1:]:
		if item.startswith("--"):
			continue
		return Path(item)
	return Path(os.getcwd())

# process current directory
def main():
	process_file()

def build() -> dict:
	process_file()
	path = util.ARGS.output / ("." + util.ARGS.path.stem + ".json")
	with open(path, "r") as file:
		data = json.load(file)
	return data

# find all the builds
def get_built():
	return file.get_paths(get_current_directory(), [], hidden="only", extensions=[".json"])

def hide_name(path):
	path = Path(path)
	return path.parent / ("." + path.stem + path.suffix)

def get_texture_directory(data):
	return Path(data["directory"]) / Path(data["settings"]["directory"])

def process_directory(directory):
	directory = Path(directory)
	
	for path in file.get_paths(directory, [], extensions=EXTENSIONS):
		process_file(path)

def make_json_safe(d):
	# make json safe for serialize
	for k in d:
		if not isinstance(d[k], (dict,list,tuple,str,int,float,bool)):
			print("JSON ", d[k])
			d[k] = str(d[k])

def process_file():
	global PROCESSORS
	
	util.init()
	path = util.ARGS.path
	
	# find settings
	settings_path, settings_time, settings = get_settings(path)
	
	# check for old data
	data = {
		"name": path.stem,
		"type": path.suffix,
		"time": file.time(path),
		"settings_time": settings_time,
		"settings": settings,
	}
	
	# import processor
	extension = path.suffix
	if not extension in PROCESSORS:
		ext2 = extension[1:]
		PROCESSORS[extension] = importlib.import_module(f".process_{ext2}", package="limage")
	
	# process
	PROCESSORS[extension].process(path, data)
	
	util.dig(data, make_json_safe)
	
	# save to disk
	info_path = util.ARGS.output / ("." + path.stem + ".json")
	file.save(data, info_path, pretty=True)

def _on_all_layers(l, func):
	func(l)
	if "layers" in l:
		for c in l["layers"]:
			_on_all_layers(c, func)

def on_all_layers(data, func):
	for l in data["root"]["layers"]:
		_on_all_layers(l, func)

def get_all_layers(data) -> list:
	out = []
	on_all_layers(data, lambda l: out.append(l))
	return out

def get_local_dir(data) -> str:
	resources_dir = os.getcwd()
	file_dir = data["directory"]
	return file_dir[len(resources_dir)+1:]

def has_tag(layer, tag) -> bool:
	if isinstance(tag, str):
		return tag in layer["tags"]
	
	elif isinstance(tag, list):
		for t in tag:
			if t in layer["tags"]:
				return True
		return False
		