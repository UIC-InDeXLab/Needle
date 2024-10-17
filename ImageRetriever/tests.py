import os
import unittest

from PIL import Image

from models import ImageFile
from test_utils import create_test_image, move_file
from utils import get_tiles


class TestGetImageTiles(unittest.TestCase):
    def setUp(self):
        create_test_image()

    def tearDown(self):
        move_file("output_tiles/main_image.png")

    def test_get_tiles(self):
        # Read the image file
        image_path = 'test_image.png'
        image = ImageFile(image_path)
        # Generate tiles
        tiles = get_tiles(image, min_patch_size=224)

        # Create a directory to save tiles if it doesn't exist
        output_dir = 'output_tiles'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save each tile to disk
        for i, tile in enumerate(tiles):
            tile_path = os.path.join(output_dir, f'tile_{i}.jpg')
            tile.save(tile_path)

        print(f"{len(tiles)} tiles generated and saved in '{output_dir}' directory.")
