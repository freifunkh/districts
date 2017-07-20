#!/usr/bin/python3

import argparse
import json

# Definitions:
# - A coordinate is a float representing the longitude or latitude, like 9.72839349542828 or 52.427206400296.
# - A coord-set is a list containing a longitude and a latitude (in this order).
# - A polygon is a list of coord-sets.
# - A district is a list of polygons.

def sort_values( v0, v1 ):
    if v0 > v1:
        return ( v1, v0 )
    return ( v0, v1 )


def close_enough( a, b ):
    border = 0.000000001
    return ( max(a, b) - min(a, b) < border )


def is_point_on_line_segment( px, py, l0x, l0y, l1x, l1y ):
    if l0x == l1x:
        small_y, big_y = sort_values( l0y, l1y )
        return ( px == l0x and small_y <= py <= big_y )
    m = (l1y-l0y)/(l1x-l0x)
    point_on_line = close_enough( (m*(px-l0x)+l0y), py )
    small_x, big_x = sort_values( l0x, l1x )
    return ( point_on_line and small_x <= px <= big_x )


def point_crosses_line_segment( px, py, l0x, l0y, l1x, l1y ):
    '''Draws a horizontal line from the point to the right and checks whether it crosses the line.
    We have two line segments ("Strecken"), one going from our point p to the right (to infinity) and the other one
    is the given line segment.
    This is the plan:
    1. We calculate the lines ("Geraden") that contain our line segments.
    2. We calculate where these lines intersect.
    3. We check whether that point of intersection lies on both line segments. If it does, the line segments intersect.'''

    ml = 0
    try:
        ml = (l1y-l0y)/(l1x-l0x)
    except ZeroDivisionError:
        ml = (l1y-l0y)/(l1x-l0x+0.00001) # ähem...
    if ml == 0: # line is horizontal
        small_x, big_x = sort_values( l0x, l1x )
        return ( py == l0y and px <= big_x )
    # y=m*x+n ("Geradengleichung")
    np = py
    nl = l0y-(ml*l0x)
    x = (np-nl)/ml
    infinity = px+500 # Okay, that's not infinity, but it's close enough for our use case.
    is_a = is_point_on_line_segment( x, py, l0x, l0y, l1x, l1y )
    is_b = is_point_on_line_segment( x, py, px, py, infinity, py )
    return is_a and is_b
    #return ( is_point_on_line_segment( x, py, l0x, l0y, l1x, l1y ) and is_point_on_line_segment( x, py, px, py, infinity, py ) )


def is_point_in_polygon( px, py, polygon ):
    '''This function gets a point and polygon. The polygon is a list of lists containing two floats each.
    It draws a line from the point to the right (to infinity) and checks how many times it intersects the polygon borders.
    There are four cases:
    1. It does not intersect => point is outside
    2. The number of intersections is even => point is outside
    3. The number of intersections is odd => point is inside
    4. The number of intersections is infinit => point is exactly on a border of the polygon. We better check that first to avoid exceptions.'''
    x = 0
    y = 1
    intersections = 0
    line_count = len(polygon)
    for i in range(line_count-1):
        j = i+1
        # Two points make a line segment ("Strecke").
        if point_crosses_line_segment( px, py, polygon[i][x], polygon[i][y], polygon[j][x], polygon[j][y] ):
            intersections += 1
    return ( intersections%2 != 0 )


def find_district(districts, lon, lat, default):
    for district in districts:
        for polygon in districts[district]:
            if is_point_in_polygon( lon, lat, polygon ):
                return district
    return default


def sanitize_district(district):
    district = district.lower()
    district = district.replace(' ', '')
    district = district.replace('-', '')
    district = district.replace('ä', 'ae')
    district = district.replace('ö', 'oe')
    district = district.replace('ü', 'ue')
    district = district.replace('ß', 'ss')
    return district


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A script to add districts to a Freifunk nodes.json. Needs a GeoJSON file to get the data from.')
    parser.add_argument('--default-district', help="Used if a node isn't in any other district. Defaults to 'Default'.", default='Default')
    parser.add_argument('-n', '--output-nodes-json', help='Output nodes.json file.')
    parser.add_argument('-m', '--output-migrate-folder', help='Output folder for router files.')
    parser.add_argument('-x', '--output-outsiders-json', help='Output outsiders.json file, showing only nodes who are in no given district.')
    parser.add_argument('-w', '--whitelist-file', help='Use a whitelist for the districts (one name per line). If the district name is not in the list, the default name is used.')
    parser.add_argument('-s', '--sanitize-districts', help='Remove some special characters from district names and convert them to lower case.', action="store_true")
    parser.add_argument('nodesJSON', help='Path to the nodes.json file.')
    parser.add_argument('geoJSON', help='Path to the GeoJSON file containing information about the districts.')
    args = parser.parse_args()

    districts = dict()
    with open(args.geoJSON, 'r') as f:
        data = json.load(f)
        for district in data['features']:
            name = district['properties']['STADTTLNAM']
            if not name:
                continue
            districts[name] = []
            if district['geometry']['type'] == 'MultiPolygon':
                for subpoly in district['geometry']['coordinates']:
                    districts[name].append( subpoly )
            else:
                districts[name] = district['geometry']['coordinates']

    nodes_json = None
    with open(args.nodesJSON, 'r') as f:
        nodes_json = json.load(f)

    whitelist = None
    if args.whitelist_file:
        whitelist = set(line.strip() for line in open(args.whitelist_file))

    outsiders = json.loads('{"type": "FeatureCollection","features": []}')

    for node_id in nodes_json['nodes']:
        if not 'location' in nodes_json['nodes'][node_id]['nodeinfo']:
            nodes_json['nodes'][node_id]['nodeinfo']['location'] = {}

        district = args.default_district
        try:
            lat = nodes_json['nodes'][node_id]['nodeinfo']['location']['latitude']
            lon = nodes_json['nodes'][node_id]['nodeinfo']['location']['longitude']
            district = find_district( districts, lon, lat, args.default_district )

            if args.output_outsiders_json and district == args.default_district:
                outsider = json.loads('{"type": "Feature","properties": {},"geometry": {"type": "Point", "coordinates": []}}')
                outsider['properties']['name'] = node_id
                outsider['geometry']['coordinates'].append(lon)
                outsider['geometry']['coordinates'].append(lat)
                outsiders['features'].append(outsider)
        except KeyError:
            pass

        if args.sanitize_districts:
            district = sanitize_district(district)

        if whitelist and not district in whitelist:
            district = args.default_district

        nodes_json['nodes'][node_id]['nodeinfo']['location']['district'] = district
        if args.output_migrate_folder:
            migrate_file = args.output_migrate_folder + '/' + node_id
            with open(migrate_file, 'w') as f:
                f.write(district+'\n')

    if args.output_nodes_json:
        with open(args.output_nodes_json, 'w') as f:
            json.dump(nodes_json, f)

    if args.output_outsiders_json:
        with open(args.output_outsiders_json, 'w') as f:
            json.dump(outsiders, f)
