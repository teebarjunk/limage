# for generating renpy "layeredimage"
# not finished

import limage

data = limage.build("./rabbit.ora")

always = []
groups = {}
images = []

def on_layer(l):
    a = l["area"]
    print(l["name"], l["full_path"], a["x"], a["y"])
    if limage.has_tag(l, "options"):
       groups[l["name"]] = []
    elif limage.has_tag(l, "option"):
        groups[l["tags"]["option"]].append(l)
        images.append(l)
    else:
        always.append(l)
        images.append(l)

limage.on_all_layers(data, on_layer)

out = ""

out += "init python:\n"
for l in images:
    l_code = "rabbit_" + "_".join(l["full_path"])
    l_path = "rabbit/" + l["texture"]
    out += f"\trenpy.image(\"{l_code}\", \"{l_path}\")\n"

out += f"layeredimage {data['name']}:\n"

if always:
    out += "\talways:\n"
    for l in always:
        l_name = "_".join(l["full_path"])
        l_x = l["area"]["x"]
        l_y = l["area"]["y"]
        out += f"\t\toffset ({l_x}, {l_y})\n"
        out += f"\t\t\"{l_name}\"\n"

if groups:
    for group in groups:
        out += f"\tgroup {group}:\n"
        for l in groups[group]:
            l_name = l['name']
            l_data = ""
            if limage.has_tag(l, "default"):
                l_data += " default"
            l_x = l["area"]["x"]
            l_y = l["area"]["y"]
            out += f"\t\tattribute {l_name}{l_data}:\n"
            out += f"\t\t\toffset ({l_x}, {l_y})\n"

out = out.replace("\t", "    ")
print(out)

with open("./li_rabbit.rpy", "w") as file:
    file.write(out)

