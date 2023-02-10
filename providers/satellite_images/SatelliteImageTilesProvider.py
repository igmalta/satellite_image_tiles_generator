import cv2
import geopandas as gpd
import numpy as np
import os
import rasterio
from providers.data.RasterProperties import RasterProperties
from providers.data.TasseledCapCoef import TasseledCapCoef
from rasterio.features import rasterize
from rasterio.windows import Window
from typing import List


class SatelliteImageTilesProvider:

    def tasseled_cap_transformation(self, array_tile: np.array) -> np.array:
        """Apply transformation Tasseled Cap."""

        transformations = [
            np.expand_dims((array_tile * transformation.coef).sum(axis=0), axis=0) for transformation in
            TasseledCapCoef]

        return np.concatenate(transformations, axis=0)

    def generate_mask(self, tile_df: gpd.GeoDataFrame, tile_window: Window):
        geometries = list(tile_df.geometry)
        mask = rasterize(geometries, out_shape=(tile_window.height, tile_window.width))

        return np.expand_dims(mask, axis=0)

    def get_tile_arrays(
            self, tile_geometries: List, raster: RasterProperties
    ) -> list[np.array]:
        with rasterio.open(os.path.join(raster.path, raster.name)) as src:
            arrays = []
            for tile_df, tile_window in tile_geometries:
                src_window = src.read(raster.bands, window=tile_window)

                # Get transformed image
                img = self.tasseled_cap_transformation(src_window)

                img = np.transpose(img, (2, 1, 0))
                img = (img * 255).astype(np.uint8)

                # Get mask
                mask = self.generate_mask(tile_df, tile_window)
                arrays.append(np.concatenate((mask, img), axis=0))

        return arrays
