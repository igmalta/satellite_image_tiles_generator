import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from geopandas import GeoDataFrame


def load_gdf_shape_file(file_path: str) -> GeoDataFrame:
    """Load shape file as a geopandas dataframe."""
    return gpd.read_file(file_path)


def load_raster(file_path: str) -> gpd.GeoDataFrame:
    """Load shape file as a geopandas dataframe."""

    with rasterio.open(file_path) as raster:
        return raster


def display_generated_tiles(array: np.array):
    raster_tile = array[0, :, :]
    masked_tile = array[2, :, :]

    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    ax[0].imshow((raster_tile * 255).astype(np.uint8))
    ax[1].imshow((masked_tile * 255).astype(np.uint8))

    return fig
