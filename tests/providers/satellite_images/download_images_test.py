import unittest
from pathlib import Path

from providers.satellite_images.download_images import download_satellite_images


class DownloadImagesTest(unittest.TestCase):

    def setUp(self):
        self.base_dir = f"{str(Path(__file__).resolve().parent.parent.parent)}/resources"

    def test_download_images_oct(self):
        aoi_file_path = f"{self.base_dir}/shapes/shape_test/test_envelope.shp"
        start_date = "2021-10-01"
        end_date = "2021-10-31"
        folder_name = "raster_test"

        download_satellite_images(aoi_file_path, start_date, end_date, folder_name)

        self.assertTrue(True)

    def test_download_images_nov(self):
        aoi_file_path = f"{self.base_dir}/shapes/shape_test/test_envelope.shp"
        start_date = "2021-11-01"
        end_date = "2021-11-30"
        folder_name = "raster_test"

        download_satellite_images(aoi_file_path, start_date, end_date, folder_name)

        self.assertTrue(True)

    def test_download_images_dic(self):
        aoi_file_path = f"{self.base_dir}/shapes/shape_test/test_envelope.shp"
        start_date = "2021-12-01"
        end_date = "2021-12-31"
        folder_name = "raster_test"

        download_satellite_images(aoi_file_path, start_date, end_date, folder_name)

        self.assertTrue(True)

    def test_download_images_mar(self):
        aoi_file_path = f"{self.base_dir}/shapes/shape_test/test_envelope.shp"
        start_date = "2022-03-01"
        end_date = "2022-03-31"
        folder_name = "raster_test"

        download_satellite_images(aoi_file_path, start_date, end_date, folder_name)

        self.assertTrue(True)

    def test_download_images_abr(self):
        aoi_file_path = f"{self.base_dir}/shapes/shape_test/test_envelope.shp"
        start_date = "2022-04-01"
        end_date = "2022-04-30"
        folder_name = "raster_test"

        download_satellite_images(aoi_file_path, start_date, end_date, folder_name)

        self.assertTrue(True)

    def test_download_images_may(self):
        aoi_file_path = f"{self.base_dir}/shapes/shape_test/test_envelope.shp"
        start_date = "2022-05-01"
        end_date = "2022-05-31"
        folder_name = "raster_test"

        download_satellite_images(aoi_file_path, start_date, end_date, folder_name)

        self.assertTrue(True)
