"""KML / KMZ read/write.

KML is Google Earth's XML format. KMZ is a zipped KML (optionally with
assets); we read the first ``.kml`` entry and ignore any embedded images or
resources. Output is a single Placemark with a LineString geometry.
"""
from __future__ import annotations

import io
import zipfile

from lxml import etree

#: KML 2.2 XML namespace.
KML_NS = 'http://www.opengis.net/kml/2.2'
NSMAP = {'kml': KML_NS}


def parse_kml(data: bytes) -> list[list[float]]:
    """Return coordinates from all ``<LineString>`` elements in a KML file.

    Falls back to any bare ``<coordinates>`` element (covers some non-standard
    exports that omit the enclosing LineString).
    """
    root = etree.fromstring(data)
    coords: list[list[float]] = []
    for el in root.iterfind('.//kml:LineString/kml:coordinates', NSMAP):
        if el.text:
            coords.extend(_parse_coord_string(el.text))
    if not coords:
        for el in root.iterfind('.//kml:coordinates', NSMAP):
            if el.text:
                coords.extend(_parse_coord_string(el.text))
    return coords


def parse_kmz(data: bytes) -> list[list[float]]:
    """Unzip a KMZ in memory and parse the embedded KML."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        kml_name = next((n for n in zf.namelist() if n.lower().endswith('.kml')), None)
        if not kml_name:
            raise ValueError('KMZ contains no .kml file')
        return parse_kml(zf.read(kml_name))


def serialize_kml(route) -> bytes:
    """Emit a minimal KML document containing the route as one LineString."""
    root = etree.Element(f'{{{KML_NS}}}kml', nsmap={None: KML_NS})
    doc = etree.SubElement(root, f'{{{KML_NS}}}Document')
    etree.SubElement(doc, f'{{{KML_NS}}}name').text = route.name
    if route.description:
        etree.SubElement(doc, f'{{{KML_NS}}}description').text = route.description
    pm = etree.SubElement(doc, f'{{{KML_NS}}}Placemark')
    etree.SubElement(pm, f'{{{KML_NS}}}name').text = route.name
    line = etree.SubElement(pm, f'{{{KML_NS}}}LineString')
    # tessellate=1 drapes the line on the terrain surface in Google Earth.
    etree.SubElement(line, f'{{{KML_NS}}}tessellate').text = '1'
    # KML coordinate strings are "lng,lat[,ele]" with whole tuples space-separated.
    coord_strs = [','.join(str(v) for v in c) for c in route.coordinates]
    etree.SubElement(line, f'{{{KML_NS}}}coordinates').text = ' '.join(coord_strs)
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)


def serialize_kmz(route) -> bytes:
    """Zip a generated KML into a single-file KMZ archive."""
    kml_bytes = serialize_kml(route)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', kml_bytes)
    return buf.getvalue()


def _parse_coord_string(text: str) -> list[list[float]]:
    """Parse KML's ``"lng,lat,ele lng,lat,ele ..."`` whitespace-separated format."""
    out: list[list[float]] = []
    for tok in text.split():
        parts = tok.strip().split(',')
        if len(parts) < 2:
            continue
        try:
            c = [float(parts[0]), float(parts[1])]
            if len(parts) >= 3:
                c.append(float(parts[2]))
            out.append(c)
        except ValueError:
            # Skip malformed tuples silently — some KML exporters emit
            # trailing whitespace or empty tokens between points.
            continue
    return out
