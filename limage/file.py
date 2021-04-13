from pathlib import Path
import json, yaml, math
from . import util
from .util import print, print_error, print_warning, get

def load_yaml_dict(f,p,**k):
	d = yaml.safe_load(f)
	return d if isinstance(d, dict) else {}

FILE_LOAD:dict = {
	".txt": lambda f,p,**k: f.read(),
	".json": lambda f,p,**k: json.load(f),
	".yaml": load_yaml_dict
}

FILE_SAVE:dict = {
	".txt": lambda f,p,d,**k: f.write(d),
	".json": lambda f,p,d,**k: f.write(util.to_json(d, **k))
}

def time(p) -> str:
	p = Path(p)
	return "" if not p.exists() else str(p.stat().st_mtime)

def size(p) -> str:
	p = Path(p)
	return "" if not p.exists() else f"({nice_bytes(p.stat().st_size, 1)})"

def nice_bytes(size:int, precision:int=2) -> str:
	for suffix in ["b", "kb", "mb", "gb", "tp", "pb"]:
		if size > 1024:
			size /= 1024.0
		else:
			return f"{round(size, precision)} {suffix}"

def collect_dirs(d, out, **kwargs) -> list:
	d = Path(d)
	out.append(d)
	for f in d.iterdir():
		# hidden?
		if f.name[0] == ".":
			if "hidden" in kwargs:
				if not kwargs["hidden"]:
					continue
			else:
				continue
		
		if f.is_dir():
			collect_dirs(f, out)
	return out

def collect_files(d, out, **kwargs) -> list:
	d = Path(d)
	for f in d.iterdir():
		# hidden?
		if f.name[0] == ".":
			if "hidden" in kwargs:
				if kwargs["hidden"] == False:
					continue
			else:
				continue
		else:
			if "hidden" in kwargs and kwargs["hidden"] == "only":
				continue
		
		if f.is_file():
			if "extensions" in kwargs:
				if not f.suffix in kwargs["extensions"]:
					continue
			out.append(f)

def get_paths(directory, out:list, **kwargs) -> list:
	directory = Path(directory)
	if not directory.exists():
		print_warning(f"no directory {directory}")
	else:
		for d in collect_dirs(directory, [], **kwargs):
			collect_files(d, out, **kwargs)
	return out

def make_dir(directory):
	directory = Path(directory)
	if not directory.exists():
		directory.mkdir(parents=True)
		print(f"created {directory}")

def load(path, default=None, **kwargs):
	path = Path(path)
	loader = path.suffix
	
	if not path.exists():
		print_warning(f"no file at {path}")
		return default
	
	if not loader in FILE_LOAD:
		print_warning(f"no loader for {path.suffix} ({path.name})")
		return default
	
	with open(path, "r") as file:
		data = FILE_LOAD[loader](file, path, **kwargs)
	
	return data

def save(data, path, **kwargs):
	path = Path(path)
	saver = path.suffix
	
	if not saver in FILE_SAVE:
		if isinstance(data, str):
			saver = ".txt" # default string saver
		elif isinstance(data, dict):
			saver = ".json" # default dict saver
		else:
			print_warning(f"no saver for {path.suffix} ({path.name})")
			return default
	
	make_dir(path.parent)
	
	with open(path, "w") as file:
		FILE_SAVE[saver](file, path, data, **kwargs)
	
	print(f"saved: {path}")