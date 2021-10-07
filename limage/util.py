from inspect import stack
from pathlib import Path
import json, os, sys, argparse, logging

EXTENSIONS:list = [".psd", ".kra", ".ora"]
SETTINGS:dict = {}
ARGS = None
_warnings = 0
_errors = 0
_print = print
indent = 0

def init():
	global ARGS
	
	parser = argparse.ArgumentParser(description="Limage v1.0")
	parser.add_argument("path", help="Path to file or directory.")
	parser.add_argument("--format", type=str, default="PNG", help="Output texture format.")
	parser.add_argument("--output", type=str, default="", help="Where to store files.")
	parser.add_argument("--scale", type=float, default=0.0, help="Scale of textures.")
	parser.add_argument("--padding", type=int, default=1, help="Extra padding around textures.")
	parser.add_argument("--quant", type=str, default="0,0,0", help="Quantize. Reduce file size at cost of color count.")
	parser.add_argument("--origin", default="0.0,0.0", help="Origin. 0.5,0.5 is center.")
	parser.add_argument("--seperator", default="-", help="Image name seperator.")
	
	parser.add_argument("--print", action="store_true", help="Debug: Print output.")
	parser.add_argument("--skip_images", action="store_true", help="Debug: Skip generating images.")
	ARGS = parser.parse_args()
	
	ARGS.path = Path(ARGS.path)
	ARGS.output = Path(ARGS.output) if ARGS.output else ARGS.path.parent / ARGS.path.stem
	
	if ARGS.path.is_dir():
		_print("must be file")
		sys.exit()
	
	elif not ARGS.path.suffix in EXTENSIONS:
		_print(f"only files of type {EXTENSIONS} allowed.")
		sys.exit()
	
	elif not ARGS.path.exists():
		_print(f"no file at {ARGS.path}")
		sys.exit()
	
	else:
		ARGS.output.mkdir(parents=False, exist_ok=True)
		
		log_path = ARGS.output / f".{ARGS.path.stem}.log"
		logging.basicConfig(filename=log_path, level=logging.DEBUG)

def _get_color_str(default, **kwargs):
	return get(kwargs, "color", default)

def _get_print_str(*args):
	return " ".join([str(x) for x in args])#.split("\n")

def _get_stack_str(s):
	s = s[1]
	script_name = s[1].rsplit('/', 1)[1]
	script_line = s[2]
	script_func = s[3]
	return f"\t<{script_name}:{script_line} @ {script_func}>"

def _compile_str(clr, lines, stk):
	tabs = "  " * indent
	called_from_outside = "called_from" in SETTINGS
	out = []
	for i in range(len(lines)):
		head = tabs + lines[i]
		tail = ""
		if i == 0:
			line_len = len(head) + len(stk)
			tail = " " * (200 - line_len)
			tail += stk
		else:
			head = "  " + head
		
		if called_from_outside:
			out.append(f"{clr}\t\t{head}\t\t{tail}")
		else:
			out.append(f"{head}{tail}")
	return "\n".join(out)

def print(*args, **kwargs):
	clr = _get_color_str("white", **kwargs)
	txt = _get_print_str(*args)
	stk = _get_stack_str(stack())
	msg = f"{txt} {stk}"# _compile_str(clr, txt, stk)
	logging.info(msg)
	if not ARGS or ARGS.print:
		_print(msg)
	

def print_error(e:Exception, path):
	global _errors
	_errors += 1
	clr = _get_color_str("red")
	txt = _get_print_str(f"{e.__class__.__name__} in {path}\n{e}")
	stk = _get_stack_str(stack())
	msg = f"{txt} {stk}"
	logging.error(msg)
	if not ARGS or ARGS.print:
		_print(msg)

def print_warning(*args):
	global _warnings
	_warnings += 1
	clr = _get_color_str("yellow")
	txt = _get_print_str("WARNING -", *args)
	stk = _get_stack_str(stack())
	msg = f"{txt} {stk}"
	logging.warning(msg)
	if not ARGS or ARGS.print:
		_print(msg)

def print_json(d, **kwargs):
	clr = _get_color_str("cyan", **kwargs)
	txt = _get_print_str(json.dumps(d, indent=4))
	stk = _get_stack_str(stack())
	msg = _compile_str(clr, txt, stk)
	logging.info(msg)
	if not ARGS or ARGS.print:
		_print(msg)

def to_json(data:dict, **kwargs) -> str:
	if "pretty" in kwargs and kwargs["pretty"]:
		return json.dumps(data, allow_nan=False, ensure_ascii=False, indent=4)
	else:
		return json.dumps(data, allow_nan=False, ensure_ascii=False, separators=(',', ':'))

def to_json_safe(data:dict, **kwargs) -> str:
	# sanitize
	def clean(d):
		for k, v in d.items():
			if isinstance(v, float):
				if v in [float('Infinity'), float('-Infinity'), float('NaN')]:
					d[k] = str(v)
	dig(data, clean)
	return to_json(data, **kwargs)

def get(d:dict, k:str, default=None):
	if isinstance(d, (list, tuple)):
		if k >= 0 and k < len(d):
			return d[k]
	elif isinstance(d, dict):
		if k in d:
			return d[k]
	return default

def remove_empty(d:dict):
	for k, v in list(d.items()):
		if v == None:
			del d[k]
	return d

def first_key(d:dict): return None if len(d) == 0 else next(iter(d))
def get_first(d): return d[first_key(d)]


def path(p) -> list:
	if isinstance(p, list):
		return p
	return p.split(":")

def str2var(s:str) -> object:
	s = s.strip()
	try:
		return int(s)
	except:
		try:
			return float(s)
		except:
			l = s.lower()
			if l == "true": return True
			if l == "false": return False
			return s

def dict2str(data:dict) -> str:
	return json.dumps(data, separators=(',', ':'))

def merge(t:dict, p:dict) -> dict:
	for k in p:
		t[k] = p[k]
	return t

def merge_unique(t:dict, p:dict) -> dict:
	for k in p:
		if not k in t:
			t[k] = p[k]
	return t

# def tiny(f): return int(f) if int(f)==f else f
# def tiny_vec2(d): return [tiny(d["x"]), tiny(d["y"])]
# def tiny_vec4(d): return [tiny(d["x"]), tiny(d["y"]), tiny(d["w"]), tiny(d["h"])]

def sanitize(s:str):
	out = ""
	for c in s:
		if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -=_/[]()<>":
			out += c
	return out.strip()

def get_between(name:str, tag1="[", tag2="]"):
	if tag1 in name:
		name, inner = name.split(tag1, 1)
		if tag2 in inner:
			inner, _ = inner.split(tag2, 1)
	else:
		return name, {}
	
	data = {}	
	for k in inner.split(" "):
		if "=" in k:
			k, v = k.split("=", 1)
			data[k] = str2var(v)
		else:
			data[k] = True
	
	name = name.strip()
	return name, data

def parse_name(name:str) -> tuple:
	name = sanitize(name)
	name, descendants_data = get_between(name, "((", "))")
	name, child_data = get_between(name, "(", ")")
	name, data = get_between(name, "[", "]")
	
	# make safe
	if False:
		name = name.lower().replace(" ", "_")
	
	return name, data, child_data, descendants_data

def append_unique(t:list, p:list):
	for item in p:
		if not item in t:
			t.append(item)
	return t

dig_path:list = []
dig_key = ""
dig_index = -1
dig_path_dict:list = [] # only dict keys

def dig(d:dict, function) -> None:
	global dig_path, dig_key, dig_index, dig_path_dict
	
	if isinstance(d, dict):
		function(d)
		
		dig_path.append(None)
		dig_path_dict.append(None)
		
		for k in list(d):
			dig_key = k
			dig_path[-1] = k
			dig_path_dict[-1] = d[k]
			dig(d[k], function)
				
		dig_path.pop()
		dig_path_dict.pop()
	
	elif isinstance(d, list):
		for i in range(len(d)):
			dig_index = i
			dig(d[i], function)