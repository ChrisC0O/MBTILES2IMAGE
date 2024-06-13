from alive_progress import alive_bar
from time import gmtime, strftime
from datetime import timedelta
from PIL import Image
import sqlite3
import pyvips
import time
import sys
import os
import gc

Image.MAX_IMAGE_PIXELS = None

class OpenMbTilesSQL:

    def __init__(self, mbtiles_filepath):
        self.db = sqlite3.connect(mbtiles_filepath)

    def get_image(self, zoom, column, row):
        zoom, column, row = str(zoom), str(column), str(row)
        query = f'SELECT tile_data FROM tiles '\
                f'WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?;'
        cur = self.db.execute(query, (zoom, column, row))
        results = cur.fetchall()
        if not results:
            return None

        return results[0][0]

    def is_image(self, zoom, column, row):
        zoom, column, row = str(zoom), str(column), str(row)
        query = f'SELECT zoom_level FROM tiles '\
                f'WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?;'
        cur = self.db.execute(query, (zoom, column, row))
        results = cur.fetchall()
        if not results:
            return False

        return True

    def get_zoom_levels(self):

        return_array = []
        query = 'SELECT DISTINCT zoom_level FROM tiles'
        cur = self.db.execute(query)
        results = cur.fetchall()
        if not results:
            return None

        for i in results:
            i = i[0]
            return_array.append(int(i))
        return return_array

    def count_tiles(self, zoom):

        zoom = str(zoom)

        return_array = []
        query = f'SELECT zoom_level FROM tiles ' \
                f'WHERE zoom_level = {zoom};'
        cur = self.db.execute(query)
        results = cur.fetchall()
        if not results:
            return None

        for i in results:
            i = i[0]
            return_array.append(int(i))

        return return_array.count(int(zoom))

    def get_columns(self, zoom):

        zoom = str(zoom)

        return_array = []
        query = f'SELECT DISTINCT tile_column FROM tiles ' \
                f'WHERE zoom_level = {zoom};'
        cur = self.db.execute(query)
        results = cur.fetchall()
        if not results:
            return None

        for i in results:
            i = i[0]
            return_array.append(int(i))
        return return_array

    def get_rows(self, zoom, colum):

        zoom, colum = str(zoom), str(colum)

        return_array = []
        query = f'SELECT DISTINCT tile_row FROM tiles ' \
                f'WHERE zoom_level = {zoom} AND tile_column = {colum};'
        cur = self.db.execute(query)
        results = cur.fetchall()
        if not results:
            return None

        for i in results:
            i = i[0]
            return_array.append(int(i))
        return return_array


def get_params_and_dir():
    params = []
    input_folder = sys.argv[1]

    if not input_folder.endswith(".mbtiles"):
        print(f"\n{input_folder} is not a .mbtiles file.")
        sys.exit()

    if not os.path.isfile(input_folder):
        print(f"\n{input_folder} does not exist.")
        sys.exit()

    try:
        if not str(sys.argv[2]).startswith("-"):
            map_to_make = str(sys.argv[2])
        else:
            map_to_make = None
    except IndexError:
        map_to_make = None

    for i in sys.argv:
        if str(i).startswith("-"):
            params.append(str(i))

    return input_folder, map_to_make, params


def display_help():
    print("""
        Use:
            MAKE_MAPS.exe <mbtiles file> <map to make:OPTIONAL>

        Example:
            MAKE_MAPS.exe mbtilesfile.mbtiles 6 -r -k -f jpeg

        Params:
            -force  [Forces the program to unpack the .mbtiles file.
            -sql    [Loads images directly from .mbtiles. No unpacking. Does not support -f with .jpg, .jpeg]
            -info   [Displays info about the .mbtiles file]
            -r      [Reverses the colum assemble order]
            -k      [Stops deletion of TEMP files]
            -c      [Crop edges from image (WARNING RAM SENSITIVE)]
            -f      [Select filetype image will be saved as. EXAMPLE: -f .jpg]
            -s      [Sequential image loading. Might be better for pc's with low RAM]
        """)
    sys.exit()


def display_mbtiles_contents(directory):
    connection = sqlite3.connect(directory)
    cursor = connection.cursor()

    cursor.execute("SELECT zoom_level FROM tiles")

    tiles = []

    for i in cursor:
        tiles.append(i[0])

    zoom_levels = list(dict.fromkeys(tiles))

    print("CONTENTS:")
    for lev in zoom_levels:
        print(f"    ZOOM_LEVEL:{lev:>4}{tiles.count(lev):>10} TILES")

    del tiles
    del zoom_levels
    sys.exit()


def del_temp_folder():

    platform = sys.platform
    if platform == "win32":
        os.system('rmdir "./temp" /S /Q')

    if platform == "linux":
        os.system('rm "./temp" -r')


def return_time_hms():
    time_hms = strftime("%H:%M:%S", gmtime())
    return_file = [time_hms, round(time.time())]
    return return_file


def return_used_time(start_time):
    time_used = return_time_hms()[1] - start_time
    td = timedelta(seconds=time_used)
    return str(td)


def extract(directory):
    print(f"[{return_time_hms()[0]}] UNPACKING {directory}...")

    start_dir = os.getcwd()

    def safeMakeDir(d):
        if os.path.exists(d):
            return
        os.makedirs(d)

    def setDir(d):
        safeMakeDir(d)
        os.chdir(d)

    input_filename = directory
    dirname = directory.split(".")[0]
    # This will fail if there is already a directory.
    # I could make a better error message, but I intend for this to fail,
    # because it's better to not delete data.
    try:
        os.makedirs(dirname)
    except FileExistsError:
        if sys.platform == "win32":
            os.system(f"rmdir {dirname} /S /Q")
        if sys.platform == "linux":
            os.system(f"rm {dirname} -r")
        os.makedirs(dirname)

    # Database connection boilerplate
    connection = sqlite3.connect(input_filename)
    cursor = connection.cursor()

    cursor.execute("SELECT value FROM metadata WHERE name='format'")
    img_format = cursor.fetchone()

    if img_format:
        if img_format[0] == 'png':
            out_format = '.png'
        elif img_format[0] == 'jpg':
            out_format = '.jpg'
    else:
        out_format = '.png'

    # The mbtiles format helpfully provides a table that aggregates all necessary info
    cursor.execute('SELECT * FROM tiles')

    os.chdir(dirname)
    for row in cursor:
        setDir(str(row[0]))
        setDir(str(row[1]))
        output_file = open(str(row[2]) + out_format, 'wb')
        output_file.write(row[3])
        output_file.close()
        os.chdir('..')
        os.chdir('..')

    os.chdir(start_dir)


def calculate_crop(image):

    def is_even(n):
        if n % 2:
            return False
        else:
            return True

    def check(listen):
        return len(set(listen)) <= 2

    WIDTH, HEIGHT = image.size[0], image.size[1]
    right, left, bottom, top, = 0, 0, 0, 0

    pixel_array = []
    run_loop = True
    for check_point_x in range(0, WIDTH):  # LEFT
        if run_loop is False:
            break
        for check_point_y in range(0, HEIGHT):
            if is_even(check_point_y) is False:
                continue
            pixel_array.append(str(image.getpixel((check_point_x, check_point_y))))

        is_array_homogeneous = check(pixel_array)

        if is_array_homogeneous is False:
            left = check_point_x
            run_loop = False
            break

        del pixel_array
        pixel_array = []

    pixel_array = []
    run_loop = True
    for check_point_x in range(0, HEIGHT):  # TOP
        if run_loop is False:
            break
        for check_point_y in range(0, WIDTH):
            if is_even(check_point_y) is False:
                continue
            pixel_array.append(str(image.getpixel((check_point_y, check_point_x))))

        is_array_homogeneous = check(pixel_array)

        if is_array_homogeneous is False:
            top = check_point_x
            run_loop = False
            break

        del pixel_array
        pixel_array = []

    pixel_array = []
    run_loop = True
    for check_point_x, return_right in zip(sorted(list(range(0, WIDTH)), reverse=True), list(range(0, WIDTH))):  # RIGHT
        if run_loop is False:
            break
        for check_point_y in range(0, HEIGHT):
            if is_even(check_point_y) is False:
                continue
            pixel_array.append(str(image.getpixel((check_point_x, check_point_y))))

        is_array_homogeneous = check(pixel_array)

        if is_array_homogeneous is False:
            right = return_right
            run_loop = False
            break

        del pixel_array
        pixel_array = []

    pixel_array = []
    run_loop = True
    for check_point_x, return_bottom in zip(sorted(list(range(0, HEIGHT)), reverse=True), list(range(0, HEIGHT))):  # BOTTOM
        if run_loop is False:
            break
        for check_point_y in range(0, WIDTH):
            if is_even(check_point_y) is False:
                continue
            pixel_array.append(str(image.getpixel((check_point_y, check_point_x))))

        is_array_homogeneous = check(pixel_array)

        if is_array_homogeneous is False:
            bottom = return_bottom
            run_loop = False
            break

        del pixel_array
        pixel_array = []

    left = left
    top = top
    right = WIDTH - (left + right)
    bottom = HEIGHT - (top + bottom)

    return_file = (left, top, right, bottom)  # PLUS MED EN FORDI RANGE STARTER PÅ 0

    return return_file


def make_paste_array(lenght, image_size):
    lenght = int(lenght)
    return_list = []
    counter = 0

    for i in range(0, lenght):
        return_list.append(counter)
        counter += image_size
    return return_list


def save_image(image, params, save_name, imagesize):

    error_message = f"\nLooks like program crashed, try using sequential image loading with: -s"
    supported_filetypes = [".png", ".jpg", ".jpeg", ".tif", ".tiff"]

    if imagesize > 64000000:
        should_bigtiff = True
    else:
        should_bigtiff = False

    if "-f" in params:
        index = sys.argv.index("-f")
        try:
            filetype = sys.argv[index + 1]
        except IndexError:
            print("\nError -f <FILETYPE> not set.\nUse -help for instructions.")
            sys.exit()

        if not filetype.startswith("."):
            filetype = f".{filetype}"

        if filetype not in supported_filetypes:
            print(f"\nFiletype <{filetype}> not supported.\nPlease select from: .png, .jpg, .jpeg, .tif, .tiff")
            sys.exit()

        if filetype in [".png", ".jpg", ".jpeg"]:
            try:
                image.write_to_file(f"{save_name}{filetype}", background=[255.0, 255.0, 255.0])
                return filetype
            except:
                print(error_message)
                sys.exit()

        if filetype in [".tif", ".tiff"]:
            try:
                image.tiffsave(f"{save_name}{filetype}", bigtiff=should_bigtiff)
                return filetype
            except:
                print(error_message)
                sys.exit()

    else:
        try:
            image.write_to_file(f"{save_name}.png", background=[255.0, 255.0, 255.0])
        except:
            print(error_message)
            sys.exit()

        return ".png"


def make_maps_disk_version(dirname, map_to_make=None, params=None):

    if not os.path.isfile(dirname):
        print(f"\n[{return_time_hms()[0]}] ERROR <{dirname}> DOES NOT EXIST!")
        sys.exit()

    if "-r" in params:
        reverse_col = False
    else:
        reverse_col = True

    if not os.path.isdir(f"./{dirname.split('.')[0]}") or "-force" in params:
        extract(dirname)

    dirname = dirname.split(".")[0]
    ALL_MAP_DIRECTORIES = os.listdir(f"{dirname}")
    ALL_MAP_DIRECTORIES.sort(key=int)

    for MAP in ALL_MAP_DIRECTORIES:

        MAP_DIRECTORIES = os.listdir(fr"./{dirname}/{MAP}")
        TILES = os.listdir(fr"./{dirname}/{MAP}/{MAP_DIRECTORIES[0]}")
        TILE_DEFAULT_DATA = pyvips.Image.new_from_file(fr"./{dirname}/{MAP}/{MAP_DIRECTORIES[0]}/{TILES[0]}")
        TILE_WEIGHT, TILE_HEIGHT = str(TILE_DEFAULT_DATA).split(" ")[1].split("x")
        IMAGE_FILETYPE = TILES[0].split(".")[1]

        TILE_WEIGHT = int(TILE_WEIGHT)
        TILE_HEIGHT = int(TILE_HEIGHT)

        use_temp_from_last_session = False

        if map_to_make is not None and not MAP == map_to_make:
            continue

        if os.path.isdir("./temp") is True and len(os.listdir(f"./temp/")) != 0:

            if os.listdir(f"./temp/")[0].split("_")[1] == f"{MAP}.png":

                y_n = input("\nProgram didn't finish from previous session.\n"
                            "Want to continue with existing TEMP files? (y/N): ")
                print("")

                if y_n.lower() == "y" or y_n.lower() == "yes":
                    use_temp_from_last_session = True

                if y_n.lower() == "n" or y_n.lower() == "no":
                    use_temp_from_last_session = False

            else:
                del_temp_folder()

        start_time = return_time_hms()[1]

        print(f"[{return_time_hms()[0]}] PROCESSING {MAP}...\n")

        all_tiles = []
        tile_matrix = []
        collums_folders = os.listdir(f"./{dirname}/{MAP}")

        collums_folders.sort(key=int)

        for col in collums_folders:
            tiles = os.listdir(f"./{dirname}/{MAP}/{col}")

            for i in tiles:
                try:
                    value = int(i.split(".")[0])
                except ValueError:
                    continue

                if value not in all_tiles:
                    all_tiles.append(int(i.split(".")[0]))

        all_tiles.sort(key=int)

        for temp in all_tiles:
            tile_holder = []
            for col in collums_folders:
                if os.path.isfile(f"./{dirname}/{MAP}/{col}/{temp}.{IMAGE_FILETYPE}"):
                    tile_holder.append(f"./{dirname}/{MAP}/{col}/{temp}.{IMAGE_FILETYPE}")
                else:
                    tile_holder.append(None)
            tile_matrix.append(tile_holder)

        plate_height = len(all_tiles) * TILE_HEIGHT
        plate_weight = len(collums_folders) * TILE_WEIGHT
        pixels_in_image = plate_weight * plate_height
        max_temp = 0

        if os.path.isdir("./temp") is False:
            os.mkdir("./temp")

        else:
            temp_dir = os.listdir("./temp")
            if len(temp_dir) == 0:
                pass

            else:
                sorted_temp_dir = []

                for i in temp_dir:
                    sorted_temp_dir.append(i.split("_")[0])
                sorted_temp_dir.sort(key=int)
                max_temp = sorted_temp_dir[-1]

        with alive_bar(len(tile_matrix) + 1) as bar:
            bar(0, skipped=True)
            counter = 0
            box = pyvips.Image.black(TILE_WEIGHT, TILE_HEIGHT)
            for column in tile_matrix:
                counter += 1
                image_array = []

                if use_temp_from_last_session and counter <= int(max_temp) - 1:
                    bar()
                    continue

                for tile in column:

                    if tile is None:
                        image_array.append(box)
                        continue

                    im = pyvips.Image.new_from_file(tile)
                    image_array.append(im)
                    continue

                im_column = pyvips.Image.arrayjoin(image_array)
                im_column.write_to_file(f"./temp/{counter}_{MAP}.png")
                bar()

        column_temp = os.listdir("./temp")
        column = []
        image_array = []

        for i in column_temp:
            column.append(i.split("_")[0])

        column.sort(key=int, reverse=reverse_col)

        if "-s" in params:
            for filename in column:
                im = pyvips.Image.new_from_file(f"./temp/{filename}_{MAP}.png", access="sequential")
                image_array.append(im)

        else:
            for filename in column:
                im = pyvips.Image.new_from_file(f"./temp/{filename}_{MAP}.png")
                image_array.append(im)

        im_plate = pyvips.Image.arrayjoin(image_array, across=1)

        print("")

        if "-c" in params:
            print(f"[{return_time_hms()[0]}] CROPPING {MAP}...")

            if pixels_in_image > 3250000000:
                print(f"[{return_time_hms()[0]}] !WARNING! IMAGE MIGHT BE TO BIG FOR CROPPING. PROGRAM MIGHT CRASH")

            l, t, w, h = calculate_crop(Image.fromarray(im_plate.numpy()))
            im_plate = im_plate.crop(l, t, w, h)

        print(f"[{return_time_hms()[0]}] SAVING {MAP}...")
        save_file_type = save_image(im_plate, params, f"{dirname}_MAP_{MAP}", pixels_in_image)
        time_used = return_used_time(start_time)
        print(f"[{return_time_hms()[0]}] {dirname}_MAP_{MAP}{save_file_type} SAVED! {time_used:>12} <- TIME USED\n")
        if "-k" not in params:
            del_temp_folder()
        gc.collect()


def make_maps_sql_version(dirname, map_to_make=None, params=None):

    if not os.path.isfile(dirname):
        print(f"\n[{return_time_hms()[0]}] ERROR <{dirname}> DOES NOT EXIST!")
        sys.exit()

    if "-r" in params:
        reverse_col = False
    else:
        reverse_col = True

    mbtiles = OpenMbTilesSQL(dirname)

    ALL_MAP_DIRECTORIES = mbtiles.get_zoom_levels()

    for MAP in ALL_MAP_DIRECTORIES:

        MAP_DIRECTORIES = mbtiles.get_columns(MAP)
        TILES = mbtiles.get_image(MAP, MAP_DIRECTORIES[0], mbtiles.get_rows(MAP, MAP_DIRECTORIES[0])[0])
        TILE_DEFAULT_DATA = pyvips.Image.new_from_buffer(TILES, options="")
        TILE_WEIGHT, TILE_HEIGHT = str(TILE_DEFAULT_DATA).split(" ")[1].split("x")

        TILE_WEIGHT = int(TILE_WEIGHT)
        TILE_HEIGHT = int(TILE_HEIGHT)

        use_temp_from_last_session = False

        if map_to_make is not None and not str(MAP) == map_to_make:
            continue

        if os.path.isdir("./temp") is True and len(os.listdir(f"./temp/")) != 0:

            if os.listdir(f"./temp/")[0].split("_")[1] == f"{MAP}.png":

                y_n = input("\nProgram didn't finish from previous session.\n"
                            "Want to continue with existing TEMP files? (y/N): ")
                print("")

                if y_n.lower() == "y" or y_n.lower() == "yes":
                    use_temp_from_last_session = True

                if y_n.lower() == "n" or y_n.lower() == "no":
                    use_temp_from_last_session = False

            else:
                del_temp_folder()

        start_time = return_time_hms()[1]

        print(f"[{return_time_hms()[0]}] PROCESSING {MAP}...\n")

        all_tiles = []
        tile_matrix = []
        collums_folders = mbtiles.get_columns(MAP)

        collums_folders.sort(key=int)

        for col in collums_folders:
            tiles = sorted(mbtiles.get_rows(MAP, col), reverse=True)

            for i in tiles:

                if i not in all_tiles:
                    all_tiles.append(int(i))

        all_tiles.sort(key=int)

        for temp in all_tiles:
            tile_holder = []
            for col in collums_folders:
                if mbtiles.is_image(MAP, col, temp) is True:
                    tile_holder.append([MAP, col, temp])
                else:
                    tile_holder.append(None)
            tile_matrix.append(tile_holder)

        plate_height = len(all_tiles) * TILE_HEIGHT
        plate_weight = len(collums_folders) * TILE_WEIGHT
        pixels_in_image = plate_weight * plate_height
        max_temp = 0

        if os.path.isdir("./temp") is False:
            os.mkdir("./temp")

        else:
            temp_dir = os.listdir("./temp")
            if len(temp_dir) == 0:
                pass

            else:
                sorted_temp_dir = []

                for i in temp_dir:
                    sorted_temp_dir.append(i.split("_")[0])
                sorted_temp_dir.sort(key=int)
                max_temp = sorted_temp_dir[-1]

        with alive_bar(len(tile_matrix) + 1) as bar:
            bar(0, skipped=True)
            counter = 0
            box = pyvips.Image.black(TILE_WEIGHT, TILE_HEIGHT)
            for column in tile_matrix:
                counter += 1
                image_array = []

                if use_temp_from_last_session and counter <= int(max_temp) - 1:
                    bar()
                    continue

                for tile in column:

                    if tile is None:
                        image_array.append(box)
                        continue

                    im = pyvips.Image.new_from_buffer(mbtiles.get_image(tile[0], tile[1], tile[2]), options="")
                    image_array.append(im)
                    continue

                im_column = pyvips.Image.arrayjoin(image_array)
                im_column.write_to_file(f"./temp/{counter}_{MAP}.png")
                bar()

        column_temp = os.listdir("./temp")
        column = []
        image_array = []

        for i in column_temp:
            column.append(i.split("_")[0])

        column.sort(key=int, reverse=reverse_col)

        if "-s" in params:
            for filename in column:
                im = pyvips.Image.new_from_file(f"./temp/{filename}_{MAP}.png", access="sequential")
                image_array.append(im)

        else:
            for filename in column:
                im = pyvips.Image.new_from_file(f"./temp/{filename}_{MAP}.png")
                image_array.append(im)

        im_plate = pyvips.Image.arrayjoin(image_array, across=1)

        print("")

        if "-c" in params:
            print(f"[{return_time_hms()[0]}] CROPPING {MAP}...")

            if pixels_in_image > 3250000000:
                print(f"[{return_time_hms()[0]}] !WARNING! IMAGE MIGHT BE TO BIG FOR CROPPING. PROGRAM MIGHT CRASH")

            l, t, w, h = calculate_crop(Image.fromarray(im_plate.numpy()))
            im_plate = im_plate.crop(l, t, w, h)

        print(f"[{return_time_hms()[0]}] SAVING {MAP}...")
        save_file_type = save_image(im_plate, params, f"{dirname.split('.')[0]}_MAP_{MAP}", pixels_in_image)
        time_used = return_used_time(start_time)
        print(f"[{return_time_hms()[0]}] {dirname.split('.')[0]}_MAP_{MAP}{save_file_type} SAVED! {time_used:>12} <- TIME USED\n")
        if "-k" not in params:
            del_temp_folder()
        gc.collect()



input_folder, map_to_make, params = get_params_and_dir()

if "-help" in params:
    display_help()

if "-info" in params:
    display_mbtiles_contents(input_folder)

if "-sql" in params:
    make_maps_sql_version(input_folder, map_to_make, params)
else:
    make_maps_disk_version(input_folder, map_to_make, params)
