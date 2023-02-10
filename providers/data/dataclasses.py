from dataclasses import dataclass


@dataclass
class TileParams:
    width: int
    height: int
    pixel_size: int
    min_percentage_covered_geometry: float
