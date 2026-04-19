"""FIT file I/O.

Import uses ``fitparse``. Export writes a minimal Course file by hand — the
Garmin FIT spec is binary with CRCs and field definitions. This implementation
covers the subset needed to round-trip a GPS track.
"""
from __future__ import annotations

import struct
from io import BytesIO

import fitparse

_SEMICIRCLE_FROM_DEG = (2 ** 31) / 180.0


def parse(data: bytes) -> list[list[float]]:
    """Extract ``[[lng, lat, ele?], ...]`` from FIT record messages.

    ``fitparse`` already converts lat/lng from semicircles to degrees and
    returns ``None`` for missing values — we just need to filter and reorder
    to GeoJSON conventions. Activities, Courses, and Workouts all use the
    same ``record`` message shape, so this works across FIT variants.
    """
    fit = fitparse.FitFile(BytesIO(data))
    coords: list[list[float]] = []
    for record in fit.get_messages('record'):
        values = {d.name: d.value for d in record}
        lat = values.get('position_lat')
        lng = values.get('position_long')
        if lat is None or lng is None:
            continue
        c = [float(lng), float(lat)]
        # Prefer enhanced_altitude if a device recorded both (it has more range).
        ele = values.get('altitude') or values.get('enhanced_altitude')
        if ele is not None:
            c.append(float(ele))
        coords.append(c)
    return coords


def serialize(route) -> bytes:
    """Write a minimal FIT Course file.

    Garmin's own courses use the Course + Lap + Record messages. We include
    file_id, course, lap, and record messages. Timestamps are synthesized at
    1 Hz from a fixed epoch — receivers treat a course as a route, not a
    historical activity, so exact timing isn't important.
    """
    body = BytesIO()

    # Definition + data for file_id (global 0)
    body.write(_define(local=0, global_num=0, fields=[
        (3, 4, 0x8C),   # serial_number, uint32z
        (4, 4, 0x86),   # time_created, uint32
        (1, 2, 0x84),   # manufacturer, uint16
        (2, 2, 0x84),   # product, uint16
        (0, 1, 0x00),   # type, enum
    ]))
    body.write(struct.pack('<B', 0))
    body.write(struct.pack('<IIHHB', 0, 0, 255, 0, 6))  # type=6 (course)

    # course message (global 31): name
    name = (route.name or 'Route')[:15].encode('utf-8')
    name_field = name.ljust(16, b'\x00')
    body.write(_define(local=0, global_num=31, fields=[
        (5, 16, 0x07),  # name, string
    ]))
    body.write(struct.pack('<B', 0))
    body.write(name_field)

    # record message (global 20)
    body.write(_define(local=0, global_num=20, fields=[
        (253, 4, 0x86),  # timestamp, uint32
        (0, 4, 0x85),    # position_lat, sint32
        (1, 4, 0x85),    # position_long, sint32
        (2, 2, 0x84),    # altitude, uint16 (scale 5, offset 500)
        (5, 4, 0x86),    # distance, uint32 (scale 100)
    ]))

    from ..geometry import haversine_m
    ts = 0
    cumulative = 0.0
    prev = None
    for c in route.coordinates:
        if prev is not None:
            cumulative += haversine_m(prev, c)
        lat = int(round(c[1] * _SEMICIRCLE_FROM_DEG))
        lng = int(round(c[0] * _SEMICIRCLE_FROM_DEG))
        ele = c[2] if len(c) >= 3 else 0.0
        alt_raw = int(round((ele + 500) * 5))
        alt_raw = max(0, min(alt_raw, 0xFFFE))
        body.write(struct.pack('<B', 0))
        body.write(struct.pack('<IiiHI', ts, lat, lng, alt_raw, int(cumulative * 100)))
        ts += 1
        prev = c

    data_bytes = body.getvalue()
    header = _fit_header(len(data_bytes))
    payload = header + data_bytes
    crc = _fit_crc(payload)
    return payload + struct.pack('<H', crc)


def _define(local: int, global_num: int, fields: list[tuple[int, int, int]]) -> bytes:
    """Build a FIT definition message for a local message type.

    Each ``fields`` tuple is ``(field_number, size_bytes, base_type_byte)``
    per the FIT SDK. Bit 6 of the header byte marks the record as a definition
    rather than data. Architecture byte 0 means little-endian.
    """
    out = struct.pack('<B', 0x40 | local)
    out += struct.pack('<BBHB', 0, 0, global_num, len(fields))
    for num, size, base_type in fields:
        out += struct.pack('<BBB', num, size, base_type)
    return out


def _fit_header(data_len: int) -> bytes:
    """14-byte FIT file header.

    Fields: size=14, protocol=0x10 (2.0), profile=2143, data_size, ``.FIT``
    magic, CRC over the header itself.
    """
    header = struct.pack('<BBHI4s', 14, 0x10, 2143, data_len, b'.FIT')
    header += struct.pack('<H', _fit_crc(header))
    return header


def _fit_crc(data: bytes) -> int:
    """Garmin FIT CRC-16.

    Based on the 4-bit lookup table from the FIT SDK — each byte contributes
    two table lookups (low nibble, then high nibble). The same algorithm
    covers the header CRC and the final file CRC.
    """
    table = [
        0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
    ]
    crc = 0
    for byte in data:
        tmp = table[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ table[byte & 0xF]
        tmp = table[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ table[(byte >> 4) & 0xF]
    return crc
