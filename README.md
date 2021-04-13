
## limage v0.1 - (UNSTABLE, VERY EARLY)

Decompile layered images (.psd, .ora) into cropped textures + a json data file.

Works with Krita and Gimp and anything else that can export .psd and .ora.

## Setup

**Not ready for use.**

- pip install .
- cd directory/with/files
- limage

## Command Line Flags

- --print # output print statements
- --skip_images # don't generate new images

## Features

- Many [image formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html), like WEBP.
- Scale, [quantize](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.quantize), and [optimize](#Settings) images.
- Optionally merge groups at build time, so they can stay seperate in your file.
- Only builds if there were changes.

## Tags

Add tags in layer names, between []: *layer_name [tag_1 tag2 tag-3]*

Use () to set tags for all children. *layer_group \[tag1\] (tag2 tag3)*

Use (()) to set tags for all descendants. *buttons ((button))*

Tags can have values: *background [parallax=10]* which you can then get in Godot with *limage.get_layer("background").tags.get("parallax")*.

- **x**: Completely ignore layer. (Wont export image or layer info.)
- **xtex**: Don't generate texture.
- **xdat**: Don't generate layer data.
- **!crop**: Disable auto cropping to smallest size.
- **visible**: Will make layer visible, regardless of it's state in the psd.
- **!visible**: ^
- **point**: Won't generate an image, but will create an empty node in the scene. Useful for spawn points.
- **origin**: Sets the origin of the parent group. If no parent, sets the global origin.

- **copy**: Use texture of another layer. (Useful for limbs, eyes, repeating objects...)
- **dir**: For explicitly defining local directory to save layer to. (Ideally use between children tags "()".)

### Group Tags

- **origins**: Children will be treated as points and used for layer origins, for easier rotations + scaling.
- **merge**: "Flatten" children into one image.


## Config Structures

Export settings can be tweaked by including a *.json* or *.yaml* file next to the psd, with an identical name.

So next to *layered_images/my_picture* **.psd** include *layered_images/my_picture* **.json** with your settings.

```python
# default settings
"seperator": "-",				# change to "/" and images will be stored in subfolders instead.
"directory": None,				# if set, saves textures here
"scale": 1,						# rescale textures

# in range of 0.0 - 1.0. makes rotation + flipping easier.
# creating a layer with an "origin" tag will replace this. 
"origin": [0, 0],

# you can choose any image format pillow + Godot support.
# but PNG, WEBP, and JPG are probably the most common.
# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
# https://docs.godotengine.org/en/stable/getting_started/workflow/assets/importing_images.html
"format": "PNG",

# can really decrease file size, but at cost of color range.
# https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.quantize
"quantize": False,

# default texture format settings
"PNG": {
	"optimize": True,
},

# WEBP can be A LOT smaller than png.
# If this doesnt work for you try (on Ubuntu): sudo apt-get install -y libwebp-dev
"WEBP": {
	"lossless": True,
	"method": 3,
	"quality": 80
},

"JPEG": {
	"optimize": True,
	"quality": 80
}
```

```yaml
# yaml version fwiw
seperator: "-"
directory: null
scale": 1
origin: [0, 0]
format: PNG
quantize: False

PNG:
  optimize: True

WEBP:
  lossless: True
  method: 3
  quality: 80

JPEG:
  optimize: True
  quality: 80
```

## Exported JSON Structure

Data will be exported next to the file as a hidden .json: *my_psd.psd* -> *.my_psd.json*.

```json
{
	"name": "my_psd", // Name of file, minus extension.
	"type": ".psd", // Extension.
	"directory": "", // The main directory files are in.
	
	"size": { // Size of file.
		"x": 0,
		"y": 0
	},
	"root": {	// Container for main layers.
		"layers": [
			{
				"name": "my_layer", // 
				"path": [], // List of parent group layers.
				"full_path": [], // 'path' + 'name'
				"tags": { // Optional tags included in file name. See Tags section.
					"tag1": true,
					"tag2": 10
				}, 
				"visible": true, // Was layer visible?
				"opacity": 1.0, // Layer alpha. 0.0-1.0 range.
				"blend_mode": "normal", // Blendmode normalized to snake case.
				"position": { // Position localized to group.
					"x": 0.0,
					"y": 0.0
				},
				"origin": { // Origin (typically centered). Localized to group.
					"x": 0.0,
					"y": 0.0
				},
				"area": { // Area of texture in file. Not localized to group. 
					"x": 0,
					"y": 0,
					"w": 0,
					"h": 0
				},
				
				// Only for texture layers.
				"texture": "", // Local path where texture was saved. Add to "directory" to get full path.
				"scale": 1.0, // Scale texture was saved with.
				
				// Only for group layers.
				"layers": []
			}
		]
	}
}
```

## Solutions

### WEBP

If WEBP exporting isn't working, try installing, reinstalling, or updating [PILLOW](https://pillow.readthedocs.io/en/stable/installation.html), and/or libwebp:

On Ubuntu:

```
sudo apt-get install -y libwebp-dev
```
