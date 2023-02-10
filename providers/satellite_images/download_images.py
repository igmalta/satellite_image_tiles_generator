import ee
import json
import logging
import time
from ee.geometry import Geometry
from ee.image import Image
from ee.imagecollection import ImageCollection

from conf.config import Conf
from providers.data.enums import Satellite
from utils import utils


def _get_aoi_envelope_geometry(file_path: str) -> Geometry:
    aoi_geometry_gpd = utils.load_gdf_shape_file(file_path)

    aoi_geometry_json = json.loads(aoi_geometry_gpd.to_json())
    coordinates = aoi_geometry_json["features"][0]["geometry"]["coordinates"]

    return ee.Geometry.MultiPolygon(coordinates)


def __get_s2_sr_collection(aoi: Geometry, start_date: str, end_date: str) -> ImageCollection:
    """Import and filter S2 SR. """

    cloud_filter = Conf().get_property("cloud_mask_params", "cloud_filter")

    return (ee.ImageCollection(Satellite.COPERNICUS_S2_SR.value)
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", cloud_filter))
            )


def __get_s2_cloudless_collection(aoi: Geometry, start_date: str, end_date: str) -> ImageCollection:
    """Import and filter s2cloudless."""

    return (ee.ImageCollection(Satellite.COPERNICUS_S2_CLOUD_PROBABILITY.value)
            .filterBounds(aoi)
            .filterDate(start_date, end_date))


def _get_s2_sr_cloud_collection(aoi: Geometry, start_date: str, end_date: str) -> ImageCollection:
    """Join the filtered s2cloudless collection to the SR collection by the 'system:index' property."""

    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        "primary": __get_s2_sr_collection(aoi, start_date, end_date),
        "secondary": __get_s2_cloudless_collection(aoi, start_date, end_date),
        "condition": ee.Filter.equals(**{
            "leftField": 'system:index',
            "rightField": 'system:index'
        })
    }))


def __add_cloud_bands(img: Image) -> Image:
    # Get s2cloudless image, subset the probability band.
    cloud_probability = ee.Image(img.get("s2cloudless")).select("probability")

    # Condition s2cloudless by the probability threshold value.
    cloud_probability_thresh = Conf().get_property("cloud_mask_params", "cloud_probability_thresh")
    is_cloud = cloud_probability.gt(cloud_probability_thresh).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cloud_probability, is_cloud]))


def __add_shadow_bands(img: Image) -> Image:
    # Identify water pixels from the SCL band.
    not_water = img.select("SCL").neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    nir_dark_thresh = Conf().get_property("cloud_mask_params", "nir_dark_thresh")
    dark_pixels = img.select('B8').lt(nir_dark_thresh * 1e4).multiply(not_water).rename(
        'dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')))

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cloud_projection_distance = Conf().get_property("cloud_mask_params", "cloud_projection_distance")
    cloud_projection = (
        img.select('clouds').directionalDistanceTransform(shadow_azimuth, cloud_projection_distance * 10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cloud_projection.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cloud_projection, shadows]))


def _add_cloud_shadow_mask(img: Image) -> Image:
    # Add cloud component bands.
    img_cloud = __add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = __add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cloud_shadow = img_cloud_shadow.select("clouds").add(img_cloud_shadow.select("shadows")).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    buffer = Conf().get_property("cloud_mask_params", "buffer")
    is_cloud_shadow = (
        is_cloud_shadow.focalMin(2).focalMax(buffer * 2 / 10)
        .reproject(**{"crs": img.select([0]).projection(), "scale": 10})
        .rename("cloudmask")
    )

    # Add the final cloud-shadow mask to the image.
    return img_cloud_shadow.addBands(is_cloud_shadow)


def _apply_cloud_shadow_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)


def get_image_collection(aoi: Geometry, start_date: str, end_date: str) -> ImageCollection:
    """
    https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless
    """

    s2_sr_cloud_collection = _get_s2_sr_cloud_collection(aoi, start_date, end_date)

    return (s2_sr_cloud_collection
            .map(_add_cloud_shadow_mask)
            .map(_apply_cloud_shadow_mask)
            .median())


def export_image_to_drive(
        aoi: Geometry, image: Image, start_date: str, end_date: str, folder_name: str
) -> None:
    task = ee.batch.Export.image.toDrive(**{
        "image": image,
        "fileNamePrefix": f"raster_{start_date.replace('-', '')}_{end_date.replace('-', '')}",
        "scale": 10,
        "folder": folder_name,
        "fileFormat": "GeoTIFF",
        "region": aoi,
        "maxPixels": 10000000000000
    })
    task.start()

    while task.active():
        logging.info(f"Polling for task (id: {task.id}).")
        time.sleep(10)

    print(task.status())


def download_satellite_images(aoi_file_path: str, start_date: str, end_date: str, folder_name: str) -> None:
    ee.Authenticate(auth_mode="localhost")
    ee.Initialize()

    bands = Conf().get_property("raster_files", "bands")

    aoi = _get_aoi_envelope_geometry(aoi_file_path)

    image_collection = get_image_collection(aoi, start_date, end_date)
    image_to_export = image_collection.select(bands)

    export_image_to_drive(aoi, image_to_export, start_date, end_date, folder_name)
