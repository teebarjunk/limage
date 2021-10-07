from setuptools import setup
setup(
	name='limage',
	packages=['limage'],
	version='0.3',
	description='Decompile layered images from Photoshop, Krita, Gimp...',
	keywords=["PHOTOSHOP", "KRITA", "GIMP", "LAYERED IMAGES"],
	
	license='MIT',
	url='#',
	
	author='teebar',
	author_email='teebaroen@protonmail.com',
	download_url = '',
	
	entry_points={
		'console_scripts': ['limage=limage.command_line:main'],
	},
	install_requires=[
		"numpy",
		"psd-tools",	# photoshop
		"pyora"			# open raster
	],
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Intended Audience :: Game Developers',
		'License :: OSI Approved :: MIT License',
		'Programming Language :: Python :: 3.8',
	],
	zip_safe=False
)