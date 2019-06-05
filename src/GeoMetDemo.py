#  Copyright 2013 Lars Butler & individual contributors
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import GeoMetUtil as util


def _unsupported_geom_type(geom_type):
    raise ValueError("Unsupported geometry type '%s'" % geom_type)

def dumps(obj, decimals=16):
    """
    Dump a GeoJSON-like `dict` to a WKT string.
    """
    try:
        geom_type = obj['type']
        exporter = _dumps_registry.get(geom_type)

        if exporter is None:
            _unsupported_geom_type(geom_type)

        # Check for empty cases
        if geom_type == 'GeometryCollection':
            if len(obj['geometries']) == 0:
                return 'GEOMETRYCOLLECTION EMPTY'
        else:
            # Geom has no coordinate values at all, and must be empty.
            if len(list(util.flatten_multi_dim(obj['coordinates']))) == 0:
                return '%s EMPTY' % geom_type.upper()
    except KeyError:
        raise KeyError('Invalid GeoJSON: %s' % obj)

    result = exporter(obj, decimals)
    # Try to get the SRID from `meta.srid`
    meta_srid = obj.get('meta', {}).get('srid')
    # Also try to get it from `crs.properties.name`:
    crs_srid = obj.get('crs', {}).get('properties', {}).get('name')
    if crs_srid is not None:
        # Shave off the EPSG prefix to give us the SRID:
        crs_srid = crs_srid.replace('EPSG', '')

    if (meta_srid is not None and
            crs_srid is not None and
            str(meta_srid) != str(crs_srid)):
        raise ValueError(
            'Ambiguous CRS/SRID values: %s and %s' % (meta_srid, crs_srid)
        )
    srid = meta_srid or crs_srid

    # TODO: add tests for CRS input
    if srid is not None:
        # Prepend the SRID
        result = 'SRID=%s;%s' % (srid, result)
    return result

def _round_and_pad(value, decimals):
    """
    Round the input value to `decimals` places, and pad with 0's
    if the resulting value is less than `decimals`.
    :param value:
        The value to round
    :param decimals:
        Number of decimals places which should be displayed after the rounding.
    :return:
        str of the rounded value
    """
    if isinstance(value, int) and decimals != 0:
        # if we get an int coordinate and we have a non-zero value for
        # `decimals`, we want to create a float to pad out.
        value = float(value)

    elif decimals == 0:
        # if get a `decimals` value of 0, we want to return an int.
        return repr(int(round(value, decimals)))

    rounded = repr(round(value, decimals))
    rounded += '0' * (decimals - len(rounded.split('.')[1]))
    return rounded

def _dump_point(obj, decimals):
    """
    Dump a GeoJSON-like Point object to WKT.
    :param dict obj:
        A GeoJSON-like `dict` representing a Point.
    :param int decimals:
        int which indicates the number of digits to display after the
        decimal point when formatting coordinates.
    :returns:
        WKT representation of the input GeoJSON Point ``obj``.
    """
    coords = obj['coordinates']
    pt = 'POINT (%s)' % ' '.join(_round_and_pad(c, decimals)
                                 for c in coords)
    return pt


def _dump_linestring(obj, decimals):
    """
    Dump a GeoJSON-like LineString object to WKT.
    Input parameters and return value are the LINESTRING equivalent to
    :func:`_dump_point`.
    """
    coords = obj['coordinates']
    ls = 'LINESTRING (%s)'
    ls %= ', '.join(' '.join(_round_and_pad(c, decimals)
                             for c in pt) for pt in coords)
    return ls


def _dump_polygon(obj, decimals):
    """
    Dump a GeoJSON-like Polygon object to WKT.
    Input parameters and return value are the POLYGON equivalent to
    :func:`_dump_point`.
    """
    coords = obj['coordinates']
    poly = 'POLYGON (%s)'
    rings = (', '.join(' '.join(_round_and_pad(c, decimals)
                                for c in pt) for pt in ring)
             for ring in coords)
    rings = ('(%s)' % r for r in rings)
    poly %= ', '.join(rings)
    return poly


def _dump_multipoint(obj, decimals):
    """
    Dump a GeoJSON-like MultiPoint object to WKT.
    Input parameters and return value are the MULTIPOINT equivalent to
    :func:`_dump_point`.
    """
    coords = obj['coordinates']
    mp = 'MULTIPOINT (%s)'
    points = (' '.join(_round_and_pad(c, decimals)
                       for c in pt) for pt in coords)
    # Add parens around each point.
    points = ('(%s)' % pt for pt in points)
    mp %= ', '.join(points)
    return mp


def _dump_multilinestring(obj, decimals):
    """
    Dump a GeoJSON-like MultiLineString object to WKT.
    Input parameters and return value are the MULTILINESTRING equivalent to
    :func:`_dump_point`.
    """
    coords = obj['coordinates']
    mlls = 'MULTILINESTRING (%s)'
    linestrs = ('(%s)' % ', '.join(' '.join(_round_and_pad(c, decimals)
                for c in pt) for pt in linestr) for linestr in coords)
    mlls %= ', '.join(ls for ls in linestrs)
    return mlls


def _dump_multipolygon(obj, decimals):
    """
    Dump a GeoJSON-like MultiPolygon object to WKT.
    Input parameters and return value are the MULTIPOLYGON equivalent to
    :func:`_dump_point`.
    """
    coords = obj['coordinates']
    mp = 'MULTIPOLYGON (%s)'

    polys = (
        # join the polygons in the multipolygon
        ', '.join(
            # join the rings in a polygon,
            # and wrap in parens
            '(%s)' % ', '.join(
                # join the points in a ring,
                # and wrap in parens
                '(%s)' % ', '.join(
                    # join coordinate values of a vertex
                    ' '.join(_round_and_pad(c, decimals) for c in pt)
                    for pt in ring)
                for ring in poly)
            for poly in coords)
    )
    mp %= polys
    return mp


def _dump_geometrycollection(obj, decimals):
    """
    Dump a GeoJSON-like GeometryCollection object to WKT.
    Input parameters and return value are the GEOMETRYCOLLECTION equivalent to
    :func:`_dump_point`.
    The WKT conversions for each geometry in the collection are delegated to
    their respective functions.
    """
    gc = 'GEOMETRYCOLLECTION (%s)'
    geoms = obj['geometries']
    geoms_wkt = []
    for geom in geoms:
        geom_type = geom['type']
        geoms_wkt.append(_dumps_registry.get(geom_type)(geom, decimals))
    gc %= ','.join(geoms_wkt)
    return gc

_dumps_registry = {
    'Point':  _dump_point,
    'LineString': _dump_linestring,
    'Polygon': _dump_polygon,
    'MultiPoint': _dump_multipoint,
    'MultiLineString': _dump_multilinestring,
    'MultiPolygon': _dump_multipolygon,
    'GeometryCollection': _dump_geometrycollection,
}