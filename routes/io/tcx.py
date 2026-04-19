"""TCX (Garmin Training Center XML) read/write.

TCX is XML with a rigid Garmin schema. We emit a Course (planned ride), not
an Activity (recorded ride), so Garmin devices treat the export as a route
to follow rather than historical data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from lxml import etree

#: TCX v2 XML namespace. All TCX elements must be qualified with this.
TCX_NS = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
NSMAP = {'tcx': TCX_NS}


def parse(data: bytes) -> list[list[float]]:
    """Extract trackpoints from any TCX file (Course or Activity)."""
    root = etree.fromstring(data)
    coords: list[list[float]] = []
    for tp in root.iterfind('.//tcx:Trackpoint', NSMAP):
        pos = tp.find('tcx:Position', NSMAP)
        if pos is None:
            continue
        lat_el = pos.find('tcx:LatitudeDegrees', NSMAP)
        lng_el = pos.find('tcx:LongitudeDegrees', NSMAP)
        if lat_el is None or lng_el is None:
            continue
        c = [float(lng_el.text), float(lat_el.text)]
        ele_el = tp.find('tcx:AltitudeMeters', NSMAP)
        if ele_el is not None and ele_el.text is not None:
            c.append(float(ele_el.text))
        coords.append(c)
    return coords


def serialize(route) -> bytes:
    """Write a route as a minimal TCX Course.

    Garmin caps Course names at 15 characters; longer names are truncated.
    Timestamps are set to "now" because a Course is a plan, not a record;
    devices that require timestamps won't reject the file.
    """
    root = etree.Element(f'{{{TCX_NS}}}TrainingCenterDatabase', nsmap={None: TCX_NS})
    courses = etree.SubElement(root, f'{{{TCX_NS}}}Courses')
    course = etree.SubElement(courses, f'{{{TCX_NS}}}Course')
    etree.SubElement(course, f'{{{TCX_NS}}}Name').text = route.name[:15] or 'Route'
    lap = etree.SubElement(course, f'{{{TCX_NS}}}Lap')
    etree.SubElement(lap, f'{{{TCX_NS}}}TotalTimeSeconds').text = '0'
    etree.SubElement(lap, f'{{{TCX_NS}}}DistanceMeters').text = str(route.distance_m)
    etree.SubElement(lap, f'{{{TCX_NS}}}Intensity').text = 'Active'
    track = etree.SubElement(course, f'{{{TCX_NS}}}Track')
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    for c in route.coordinates:
        tp = etree.SubElement(track, f'{{{TCX_NS}}}Trackpoint')
        etree.SubElement(tp, f'{{{TCX_NS}}}Time').text = ts
        pos = etree.SubElement(tp, f'{{{TCX_NS}}}Position')
        etree.SubElement(pos, f'{{{TCX_NS}}}LatitudeDegrees').text = str(c[1])
        etree.SubElement(pos, f'{{{TCX_NS}}}LongitudeDegrees').text = str(c[0])
        if len(c) >= 3:
            etree.SubElement(tp, f'{{{TCX_NS}}}AltitudeMeters').text = str(c[2])
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
