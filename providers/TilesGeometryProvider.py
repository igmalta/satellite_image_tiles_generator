import itertools
import logging
import os.path
from pathlib import Path

import geopandas as gdf
import numpy as np
import rasterio
from geopandas import GeoDataFrame, GeoSeries
from rasterio.features import rasterize
from rasterio.windows import Window
from shapely import geometry, affinity
from shapely.geometry import Polygon

from conf.config import Conf
from providers.data.dataclasses import TileParams
from utils import utils

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)


class TilesGeometryProvider:

    def __init__(self) -> None:
        self.base_dir = str(Path(__file__).resolve().parent.parent)
        self.tile_params = TileParams(**Conf().get_section("tile_params"))

    def __scale_to_pixel_coordinates(self, tile_geometry: GeoSeries, tile_bounds: tuple) -> GeoSeries:
        """Scale tiles polygons to defined window bounds."""

        min_x, min_y, max_x, max_y = tile_bounds
        x_coordinates, y_coordinates = tile_geometry.exterior.xy

        geom = Polygon([[x - min_x, y - min_y] for x, y in zip(x_coordinates, y_coordinates)])

        x_fact = self.tile_params.width / (max_x - min_x)
        y_fact = self.tile_params.height / (max_y - min_y)

        return affinity.scale(geom, x_fact, y_fact, origin=(0, 0, 0))

    def _invert_y_axis(self, tile_polygon: Polygon) -> Polygon:
        """Invert y-axis of the geometry."""

        x_coordinates, y_coordinates = tile_polygon.exterior.xy

        return geometry.Polygon(
            [[self.tile_params.height - y, x] for x, y in zip(x_coordinates, y_coordinates)])

    def __get_tile_geometry(self, aoi: GeoDataFrame, tile_polygon: geometry.Polygon) -> GeoSeries | None:
        """
        Make sure that the gdf is composed only of polygons (without multi polygons).
        """

        clipped_geometry = gdf.clip(aoi.geometry, tile_polygon)

        if clipped_geometry.empty:
            return None

        # Multipolygon to Polygon
        geometry_tile = clipped_geometry.explode(ignore_index=True)

        return geometry_tile[geometry_tile.geometry.to_crs({'proj': 'cea'}).area > 5000]

    def __get_percentage_covered_geometry(self, tile_geometry: GeoSeries) -> float:
        """Calculate the percentage of geometry in the tile."""

        tile_area = self.tile_params.height * self.tile_params.width * self.tile_params.pixel_size ** 2
        return tile_geometry.to_crs({'proj': 'cea'}).geometry.area.sum() / tile_area

    def _get_tiles_coordinates(self, raster_width: int, raster_height: int, start: int, stride: int) -> list:
        """Define boxes range."""

        x_coordinates = range(start, raster_width, stride)
        y_coordinates = range(start, raster_height, stride)

        return [(x, y) for x, y in itertools.product(x_coordinates, y_coordinates) if
                x + stride < raster_width or y + stride < raster_height]

    def _get_filtered_gdf_tile(
            self, aoi: GeoDataFrame, tile_window: Window, raster_meta: dict
    ) -> GeoDataFrame | None:

        tile_spatial_bounds = rasterio.windows.bounds(tile_window, raster_meta.get("transform"))

        tile_polygon = geometry.box(*tile_spatial_bounds, ccw=False)

        geometry_tile = self.__get_tile_geometry(aoi, tile_polygon)

        if geometry_tile is not None and self.__get_percentage_covered_geometry(
                geometry_tile) > self.tile_params.min_percentage_covered_geometry:
            # Scale to pixels
            scaled_geometry_tile = geometry_tile.apply(
                lambda polygon: self.__scale_to_pixel_coordinates(polygon, tile_spatial_bounds))

            # Invert y-axis (the raster images are inverted)
            scaled_geometry_tile = scaled_geometry_tile.apply(lambda polygon: self._invert_y_axis(polygon))

            return scaled_geometry_tile
        return None

    def get_tile_geometries(
            self, raster_file_path: str, shape_file_path: str, start: int, stride: int
    ) -> list:

        raster = utils.load_raster(raster_file_path)
        aoi = utils.load_gdf_shape_file(shape_file_path)

        tile_geometries = []

        tiles_coordinates = self._get_tiles_coordinates(
            raster.meta.get("width"), raster.meta.get("height"), start, stride)

        count = 0
        for (col_off, row_off) in tiles_coordinates:

            tile_window = Window(col_off, row_off, self.tile_params.width, self.tile_params.height)
            filtered_tile_geometry = self._get_filtered_gdf_tile(aoi, tile_window, raster.meta)

            if filtered_tile_geometry is not None:
                count += 1
                logging.info(f"Have been generated {count} tile geometries...")
                tile_geometries.append([filtered_tile_geometry, tile_window])

        return tile_geometries

    def _apply_tasseled_cap_transformation(self, tile_array: np.array) -> np.array:
        """Apply transformation Tasseled Cap."""

        coefficients = Conf().get_section("tasseled_cap_coefficients")

        projections = [tile_array * np.expand_dims(c, axis=(1, 2)) for c in coefficients.values()]
        projections = [np.expand_dims(p.sum(axis=0), axis=0) for p in projections]

        return np.concatenate(projections, axis=0)

    def _generate_mask(self, tile_geometry: GeoDataFrame, tile_window: Window) -> np.array:
        mask = rasterize(tile_geometry, out_shape=(tile_window.height, tile_window.width))

        return np.expand_dims(mask, axis=0)

    def get_tile_arrays(self, raster_file_path: str, tile_geometries: list, bands: list) -> list[np.array]:

        with rasterio.open(raster_file_path) as src:
            arrays = []
            bands_for_raster = range(1, len(bands) + 1)

            for tile_geometry, tile_window in tile_geometries:
                src_window = src.read(bands_for_raster, window=tile_window)

                # Get transformed image
                image = self._apply_tasseled_cap_transformation(src_window)

                # Get mask
                mask = self._generate_mask(tile_geometry, tile_window)

                arrays.append(np.concatenate((mask, image), axis=0))

        return arrays

    def save_tile_arrays(
            self,
            raster_file_path: str,
            shape_file_path: str,
            arrays_folder: str,
            start: int, stride: int,
            bands: list
    ) -> None:

        tile_geometries = self.get_tile_geometries(raster_file_path, shape_file_path, start, stride)
        tile_arrays = self.get_tile_arrays(raster_file_path, tile_geometries, bands)

        raster_id = raster_file_path.split("/")[-1]
        raster_id = raster_id.split("-")
        raster_id = f"{raster_id[0].replace('raster_', '')}_{raster_id[2].replace('.tif', '')}"

        for n, array in enumerate(tile_arrays):
            np.save(os.path.join(arrays_folder, f"array_{n}_{raster_id}"), array)
