from inspect import stack
from pathlib import Path
import json, os, sys, argparse, logging

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
	parser.add_argument("--scale", type=float, default=0.0, help="Scale of textures.")
	parser.add_argument("--padding", type=int, default=1, help="Extra padding around textures.")
	parser.add_argument("--quant", type=bool, default=False, help="Quantize. Reduce file size at cost of color count.")
	parser.add_argument("--origin", default="0.0,0.0", help="Origin. 0.5,0.5 is center.")
	parser.add_argument("--sep", default="-", help="Image name seperator.")
	
	parser.add_argument("--print", action="store_true", help="Debug: Print output.")
	parser.add_argument("--skip_images", action="store_true", help="Debug: Skip generating images.")
	ARGS = parser.parse_args()
	
	ARGS.path = Path(ARGS.path)
	ARGS.output = ARGS.path.parent / ARGS.path.stem
	
	log_path = ARGS.output / f".{ARGS.path.stem}.log"
	logging.basicConfig(filename=log_path, level=logging.DEBUG)
	
	if ARGS.path.is_dir():
		print("must be file")
		sys.exit()
	
	elif not ARGS.path.suffix in [".psd", ".ora"]:
		print("must be .psd or .ora")
		sys.exit()
	

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

# def get_between(text:str, start:str, end:str) -> list:
# 	out = []
# 	while True:
# 		a = text.find(start)
# 		if a == -1: break
# 		b = text.find(end, a + len(start))
# 		if b == -1: break
# 		out.append(text[a+len(start):b])
# 		text = text[b+len(end)+1:]
# 	return out

def tiny(f): return int(f) if int(f)==f else f
def tiny_vec2(d): return [tiny(d["x"]), tiny(d["y"])]
def tiny_vec4(d): return [tiny(d["x"]), tiny(d["y"]), tiny(d["w"]), tiny(d["h"])]

def get_between(name:str, tag1="[", tag2="]"):
	s = name.find(tag1)
	e = name.find(tag2, s+len(tag1))
	data = {}
	if s != -1 and e != -1:
		inner = name[s+len(tag1):e]
		# print(f"INNER: [{inner}]")
		
		# Replace spaces between quotes, for a second
		while True:
			qs = inner.find('"')
			qe = inner.find('"', qs+1)
			if qs != -1 and qe != -1:
				q0 = inner[:qs]
				q = inner[qs+1:qe]
				qn = inner[qe+1:]
				inner = q0 + q.replace(" ", "####") + qn
			else:
				break
		
		name = name.replace(f"{tag1}{inner}{tag2}", "")#name[:s].strip() + name[e+len(tag2):]
		inner = inner.split(" ")
		for key in inner:
			if "=" in key:
				key, val = key.split("=")
				# Return spaces to quotes.
				val = val.replace("####", " ").strip()
				data[key] = str2var(val)
			else:
				data[key] = True
	return name, data

def parse_name(name:str) -> tuple:
	name, descendants_data = get_between(name, "((", "))")
	name, child_data = get_between(name, "(", ")")
	name, data = get_between(name, "[", "]")
	
	# sanitize name
	new_name = ""
	for c in name:
		if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_ ":
			new_name += c
	new_name = new_name.strip()
	
	# make safe
	if False:
		new_name = new_name.lower().replace(" ", "_")
	
	# print(new_name, data, child_data, descendants_data)
	
	# print(output, data, child_data, descendants_data)
	return new_name, data, child_data, descendants_data

def get_between_as_flags(text:str, start:str, end:str) -> dict:
	out = {}
	for tag in get_between(text, start, end):
		for kv in tag.split(" "):
			if "=" in kv:
				k, v = kv.split("=")
				out[k] = str2var(v)
			else:
				out[kv] = True
	return out

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