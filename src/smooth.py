#! /usr/bin/python3

import gpxpy

from collections import namedtuple
import datetime
from itertools import compress, tee, chain, repeat

from .gpxtools import device
from .gpxtools import smooth
"""
Detects stops in GPX tracks based on HDOP values and simplifies these stops into less point-intensive lines.

TODO: deal with DOP increases by decreasing magic factor and enabling time margin trimming
"""


def n900_uncertainty_threshold(point):
    FACTOR = 10 # experimental
    rad = device.n900_uncertainty_m(point)
    return device.Radius(rad.horz / FACTOR, rad.vert / FACTOR)


stop_finders = {'good': smooth.find_stops2,
                'fast': smooth.find_stops}


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--method', choices=stop_finders, default='good')
    args = parser.parse_args()
    with open(args.file) as infile:
        gpx = gpxpy.parse(infile)
    
    output = sys.stdout
    
    stop_finder = stop_finders[args.method]
    
    get_uncertainty_threshold = n900_uncertainty_threshold
    for track in gpx.tracks:
        for segment in track.segments:
            clean_points = smooth.cleanup(segment.points)
            stops = stop_finder(clean_points, get_uncertainty_threshold)
            #save_segments(output, stops)
            #save_simplified_stops(output, stops, get_uncertainty_m)
            #save_movement_only(output, segment.points, stops)
            segment.points = smooth.replace_stops(clean_points, stops, get_uncertainty_threshold)
    print(gpx.to_xml(), file=output)
