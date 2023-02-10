import typer

from conf.config import Conf
from providers.TilesGeometryProvider import TilesGeometryProvider
from providers.satellite_images.download_images import download_satellite_images

# Typer CLI app
app = typer.Typer()


@app.command()
def download_images(aoi_file_path: str, start_date: str, end_date: str, folder_name: str) -> None:
    download_satellite_images(aoi_file_path, start_date, end_date, folder_name)


@app.command()
def create_tiles(raster_file_path: str, shape_file_path: str, arrays_folder: str, start: int, stride: int) -> None:
    bands = Conf().get_property("raster_files", "bands")

    tiles_geometry_provider = TilesGeometryProvider()
    tiles_geometry_provider.save_tile_arrays(raster_file_path, shape_file_path, arrays_folder, start, stride, bands)


if __name__ == '__main__':
    app()
