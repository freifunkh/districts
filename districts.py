#!/usr/bin/python3

import datetime
import argparse
import json
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def FindDistrict( districts, lon, lat, default ):
    point = Point( lon, lat )
    for district in districts:
        for coords in districts[district]:
            polygon = Polygon( coords )
            if polygon.contains( point ):
                return district
    return default


if __name__ == '__main__':
    start_time = datetime.datetime.now()
    parser = argparse.ArgumentParser(description='A script to add districts to a Freifunk nodes.json. Needs a GeoJSON file to get the data from.')
    parser.add_argument('--default-district', help="Used if a node isn't in any other district.")
    parser.add_argument('-o', '--output', help='Output file. Default is stdout.')
    parser.add_argument('nodesJSON', help='Path to the nodes.json file.')
    parser.add_argument('geoJSON', help='Path to the GeoJSON file containing information about the districts.')
    args = parser.parse_args()

    districts = dict()
    with open(args.geoJSON, 'r') as f:
        data = json.load(f)
        for district in data['features']:
            name = district['properties']['STADTTLNAM']
            if district['geometry']['type'] == 'MultiPolygon':
                districts[name] = []
                for subpoly in district['geometry']['coordinates']:
                    districts[name] += subpoly
            else:
                districts[name] = district['geometry']['coordinates']

    nodes_json = None
    with open(args.nodesJSON, 'r') as f:
        nodes_json = json.load(f)

    for node_id in nodes_json['nodes']:
        if not 'location' in nodes_json['nodes'][node_id]['nodeinfo']:
            nodes_json['nodes'][node_id]['nodeinfo']['location'] = {}
        lat = lon = 0
        try:
            lat = nodes_json['nodes'][node_id]['nodeinfo']['location']['latitude']
            lon = nodes_json['nodes'][node_id]['nodeinfo']['location']['longitude']
        except KeyError:
            pass
        nodes_json['nodes'][node_id]['nodeinfo']['location']['district'] = FindDistrict( districts, lon, lat, args.default_district )

    if args.output:
        with open(args.output, 'w') as f:
            json.dump( nodes_json, f )
    else:
        print( json.dumps( nodes_json ) )

    #print( datetime.datetime.now() - start_time )
