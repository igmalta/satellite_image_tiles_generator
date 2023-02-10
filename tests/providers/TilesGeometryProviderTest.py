import numpy as np
import pickle
import unittest
from PIL import Image
from geopandas import GeoSeries
from pathlib import Path
from rasterio.windows import Window
from shapely.geometry import Polygon

from providers.TilesGeometryProvider import TilesGeometryProvider


class TilesGeometryProviderTest(unittest.TestCase):

    def setUp(self):
        self.base_dir = f"{str(Path(__file__).resolve().parent.parent.parent)}/tests/resources"

    def test__apply_tasseled_cap_transformation(self):
        sut = TilesGeometryProvider()

        tile_array = np.ones((6, 2, 2))

        result = sut._apply_tasseled_cap_transformation(tile_array)

        self.assertEqual((3, 2, 2), result.shape)
        self.assertAlmostEqual(2.3103, result[0][0][0])
        self.assertAlmostEqual(-0.4435999999999998, result[1][0][0])
        self.assertAlmostEqual(-0.1516999999999999, result[2][0][0])

    def test__invert_y_axis(self):
        sut = TilesGeometryProvider()

        tile_polygon = Polygon(
            [[397.1765211027457, 82.17860884085565], [497.3090986368068, 0], [296.0299731659595, 0],
             [397.1765211027457, 82.17860884085565]])

        expected = Polygon(
            [[429.82139115914435, 397.1765211027457], [512, 497.3090986368068], [512, 296.0299731659595],
             [429.82139115914435, 397.1765211027457]])

        result = sut._invert_y_axis(tile_polygon)

        self.assertEqual(expected, result)

    def test_get_tile_geometries(self):
        sut = TilesGeometryProvider()

        tile_geometries = sut.get_tile_geometries(
            shape_file_path=f"{self.base_dir}/shapes/shape_train/train.shp",
            raster_file_path="",
            start=0,
            stride=128
        )

        self.assertEqual(49, len(tile_geometries))
        self.assertTrue(isinstance(tile_geometries[0][0], GeoSeries))
        self.assertTrue(isinstance(tile_geometries[0][1], Window))

        with open(f"{self.base_dir}/geometries/tile_geometries.pickle", 'wb') as f:
            pickle.dump(tile_geometries, f)

    def test_get_tile_arrays(self):
        sut = TilesGeometryProvider()

        raster_file_path = ""
        bands = ["B2", "B3", "B4", "B8", "B11", "B12"]

        with open(f"{self.base_dir}/geometries/tile_geometries.pickle", "rb") as f:
            tile_geometries = pickle.load(f)

        result = sut.get_tile_arrays(raster_file_path, tile_geometries, bands)

        self.assertTrue(isinstance(result[0], np.ndarray))
        self.assertEqual((4, 512, 512), result[0].shape)

        for n, array in enumerate(result):
            image = result[n][1:]
            image = image * 255.0 / image.max()
            image = image.astype(np.uint8)
            image = image.transpose(2, 1, 0)
            image = Image.fromarray(image, "RGB")

            image.save(f"{self.base_dir}/images/image_{n}.png")

            mask = result[n][0] * 255
            mask = mask.astype(np.uint8)
            mask = Image.fromarray(mask)
            mask.save(f"{self.base_dir}/images/mask_{n}.png")

    def test_save_tile_arrays(self):
        provider = TilesGeometryProvider()

        bands = ["B2", "B3", "B4", "B8", "B11", "B12"]

        provider.save_tile_arrays(
            shape_file_path="",
            arrays_folder="",
            raster_file_path="",
            start=0,
            stride=128,
            bands=bands
        )
