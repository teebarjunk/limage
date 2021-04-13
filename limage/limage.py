import sys, os
import importlib
from pathlib import Path
from . import __info__, file, util
from .util import get, print, print_warning, print_error

__version__ = __info__.__version__

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
	process_directory(get_current_directory())

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
	print(f"processing: {directory}")
	
	modified = {}
	for limage_path in file.get_paths(directory, [], extensions=[".psd", ".ora"]):
		
		ext = limage_path.suffix
		
		# find settings
		settings_path, settings_time, settings = get_settings(limage_path)
		
		# check for old data
		debug_data = {
			"__version__": __version__,
			"path": limage_path,
			"name": limage_path.stem,
			"type": limage_path.suffix,
			"time": file.time(limage_path),
			"directory": limage_path.parent,
			"settings_path": settings_path,
			"settings_time": settings_time,
			"settings": settings,
		}
		
		# make serializable
		for k in debug_data:
			if not isinstance(debug_data[k], (dict, list, str, bool, float, int)):
				debug_data[k] = str(debug_data[k])
		
		# todo: check for a change
		if not ext in modified:
			modified[ext] = [debug_data]
		else:
			modified[ext].append(debug_data)
	
	if len(modified) == 0:
		print(f"{directory} is up to date")
	
	else:
		# import module (.psd, .ora)...
		for ext in modified:
			print(ext)
			
			# process
			ext2 = ext[1:]
			processor = importlib.import_module(f".process_{ext2}", package="limage")
			processor.process(modified[ext])
			
			# save info
			for item in modified[ext]:
				debug_path = hide_name(item["path"]).with_suffix(".json")
				
				# make json safe for serialize
				for k in item:
					if not isinstance(item[k], (dict,list,tuple,str,int,float,bool)):
						item[k] = str(item[k])
			
				file.save(item, debug_path, pretty=True)
	
	print("done")

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