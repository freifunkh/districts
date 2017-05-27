#!/usr/bin/python3

import json
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

global_district_default = ''

def FindDistrict( districts, lon, lat ):
    point = Point( lon, lat )
    for district in districts:
        for coords in districts[district]:
            polygon = Polygon( coords )
            if polygon.contains( point ):
                return district
    return global_district_default


if __name__ == '__main__':
    districts = dict()
    with open('stadtteile.json', 'r') as f:
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
    with open('nodes.json', 'r') as f:
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
        nodes_json['nodes'][node_id]['nodeinfo']['location']['district'] = FindDistrict( districts, lon, lat )

    with open('nodes.json', 'w') as f:
        json.dump( nodes_json, f )
