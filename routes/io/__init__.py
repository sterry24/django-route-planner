"""Import/export helpers for route files.

Each submodule exposes ``parse(bytes_or_str) -> list[coord]`` and
``serialize(route) -> bytes`` where applicable.
"""
from . import fit, gpx, kml, tcx

FORMATS = {
    'gpx': ('application/gpx+xml', 'gpx'),
    'tcx': ('application/vnd.garmin.tcx+xml', 'tcx'),
    'fit': ('application/octet-stream', 'fit'),
    'kml': ('application/vnd.google-earth.kml+xml', 'kml'),
    'kmz': ('application/vnd.google-earth.kmz', 'kmz'),
}


def parse(filename: str, data: bytes) -> list[list[float]]:
    """Dispatch to the right parser based on the file extension."""
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext == 'gpx':
        return gpx.parse(data)
    if ext == 'tcx':
        return tcx.parse(data)
    if ext == 'fit':
        return fit.parse(data)
    if ext == 'kml':
        return kml.parse_kml(data)
    if ext == 'kmz':
        return kml.parse_kmz(data)
    raise ValueError(f'Unsupported file format: {ext}')


def serialize(route, fmt: str) -> tuple[bytes, str, str]:
    """Return ``(payload, content_type, extension)`` for the given route + fmt."""
    fmt = fmt.lower()
    if fmt == 'gpx':
        return gpx.serialize(route), *FORMATS['gpx']
    if fmt == 'tcx':
        return tcx.serialize(route), *FORMATS['tcx']
    if fmt == 'fit':
        return fit.serialize(route), *FORMATS['fit']
    if fmt == 'kml':
        return kml.serialize_kml(route), *FORMATS['kml']
    if fmt == 'kmz':
        return kml.serialize_kmz(route), *FORMATS['kmz']
    raise ValueError(f'Unsupported format: {fmt}')
