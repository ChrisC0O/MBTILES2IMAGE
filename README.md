# MBTILES2IMAGE
This command line tool makes images from the contents of a .mbtiles file.

### Installation:
- Install [Libvips](https://github.com/libvips/libvips) and add bin to path in environment variables.

- Install packages in requirements.txt.

### Usage:
```txt

        MBTILES2IMAGE.py <mbtiles file> <map to make:OPTIONAL>

        Example:
            MBTILES2IMAGE.py mbtilesfile.mbtiles 6 -r -k -f jpeg

        Params:
            -force  [Forces the program to unpack the .mbtiles file.
            -sql    [Loads images directly from .mbtiles. No unpacking. Does not support -f with .jpg, .jpeg]
            -info   [Displays info about the .mbtiles file]
            -r      [Reverses the colum assemble order]
            -k      [Stops deletion of TEMP files]
            -c      [Crop edges from image (WARNING RAM SENSITIVE)]
            -f      [Select filetype image will be saved as. EXAMPLE: -f .jpg]
            -s      [Sequential image loading. Might be better for pc's with low RAM]
```
