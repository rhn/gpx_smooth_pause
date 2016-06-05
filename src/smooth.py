#! /usr/bin/python3

import gpxpy

from collections import namedtuple
import datetime
from itertools import compress, tee, chain


class FutureIter:
    def __init__(self, it):
        self.it = list(it)
        self.next_ptr = 0
    
    def __iter__(self):
        for i, item in enumerate(self.it):
            if self.next_ptr > i:
                continue                
            yield item, self.it[i + 1:]
    
    def advance_after(self, item):
        self.next_ptr = self.it.index(item) + 1 # FIXME: accept indices

TRIGGER_TIME = datetime.timedelta(seconds=10)


def n900_uncertainty_m(point):
    FACTOR = 10
    horz = float(point.extensions['hdopCM']) / 100 / FACTOR
    vert = float(point.extensions['vdopCM']) / 100 / FACTOR
    return namedtuple("Uncertainty", ['horz', 'vert'])(horz, vert)

def timediff(pt1, pt2):
    return pt1.time - pt2.time


def does_overlap(it, initial, get_uncertainty):
    def check_overlap(pt, other):
        return pt.distance_2d(other) < get_uncertainty(pt).horz + get_uncertainty(other).horz
 
    checked = list(initial)
    for point in it:
        if not all(check_overlap(point, c) for c in checked):
            break
        checked.append(point)
        yield True
    yield False

def while_overlap(it, initial, get_uncertainty):
    it1, it2 = tee(it, 2)
    for i, overlap in zip(it1, does_overlap(it2, initial, get_uncertainty)):
        if not overlap:
            break
        yield i 


def is_moving(start, future, get_uncertainty):
    futures1, futures2 = tee(future, 2)
    for end, overlaps in zip(futures1, does_overlap(futures2, [start], get_uncertainty)):
        if not overlaps:
            return True
        if timediff(end, start) > TRIGGER_TIME:
            return False
    return None # not enough time points available


def until(points, time):
    for point in points:
        if point.time > time:
            return
        yield point

def split_time(points, difference):
    points = FutureIter(points)
    for start, future in points:
        segment = [start] + list(until(future, start.time + difference))
        points.advance_after(segment[-1])
        yield segment


def time_margins(it, margin):
    it = list(it)
    if len(it) == 0:
        return

    def find_idx(it, compare):
        for i, point in enumerate(it):
            if compare(point) > margin:
                return i
        return 0

    start = it[0]
    start_idx = find_idx(it, lambda point: timediff(start, point))
    end_idx = len(it) - find_idx(reversed(it), lambda point: timediff(point, start))
    return it[start_idx:end_idx]

class OnDemand:
    def __init__(self, seq):
        self.seq = seq
        self.it = None
        self.last_item = []

    def __iter__(self):
        self.it = seq.__iter__()
        while True:
            if len(self.last_item) == 0:
                self.last_item.append(self.it.next())
            yield self.last_item[-1]
    
    def next(self):
        self.last_item = []

def filter_out_segments(base, segments):
    checker = OnDemand(chain(segments))
    for point, p2 in zip(base, checker):
        if point == p2:
            checker.next()
        yield point

def find_stops(segment, get_uncertainty):
    """Good speed.
    Advances by TRIGGER_TIME or by overlapping points each time, whichever comes first.
    """
    seg_iter = FutureIter(segment)
    for point, future in seg_iter:
        stopped_points = list(while_overlap([point] + list(future), [], get_uncertainty))
        last = stopped_points[-1]
        if timediff(last, point) < TRIGGER_TIME:
            yield from (('move', point) for point in stopped_points)
        else:
            yield 'pause', stopped_points
        seg_iter.advance_after(last)


def find_stops2(segment, get_uncertainty):
    """Good sensitivity.
    Advances by overlapping points in paused mode, and by single point in moving mode. Checks for movement for each point, catching stops early and approximately in the middle.
    """
    seg_iter = FutureIter(segment)
    for point, future in seg_iter:
        if is_moving(point, future, get_uncertainty) is not False:
            yield 'move', point
            continue
        stopped_points = list(while_overlap([point] + list(future), [], get_uncertainty))
        yield 'pause', stopped_points#time_margins(stopped_points, TRIGGER_TIME / 2)
        seg_iter.advance_after(stopped_points[-1])

def weighted_average(items):
    items = list(items)
    total_weight = sum(item[1] for item in items)
    return sum(item[0] * item[1] for item in items) / total_weight

def time_average(times):
    times = list(times)
    return datetime.datetime.fromtimestamp(sum(int(time.timestamp()) for time in times) / len(times))


def find_centroid_simple(points, get_uncertainty):
    points = list(points)
    lat = weighted_average((point.latitude, 1 / get_uncertainty(point).horz) for point in points)
    lon = weighted_average((point.longitude, 1 / get_uncertainty(point).horz) for point in points)
    ele = weighted_average((point.elevation, 1 / get_uncertainty(point).vert) for point in points)
    time = time_average(point.time for point in points)
    return gpxpy.gpx.GPXTrackPoint(lat, lon, ele, time, name="stop")


def simplify_stop(points, get_uncertainty):
    for pts in split_time(points, datetime.timedelta(seconds=60)):
        yield find_centroid_simple(pts, get_uncertainty)

def replace_stops(stops_iter, get_uncertainty, skip_moves=False):
    new_points = []
    for action, data in stops_iter:
        if action == 'move' and not skip_moves:
            yield data
        elif action == 'pause':
            yield from simplify_stop(data, get_uncertainty)
        else:
            raise Exception("Invalid action")

def pauses_only(stops):
    return (stop[1] for stop in stops if stop[0] == 'pause')

def save_simplified_stops(output, stops, get_uncertainty):
    save_segments(output, (simplify_stop(seg, get_uncertainty) for seg in pauses_only(stops)))

def save_segments(output, segments):
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    for seg in segments:
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)
        segment.points.extend(seg)
    print(gpx.to_xml(), file=output)

stop_finders = {'good': find_stops2,
                'fast': find_stops}

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
    
    get_uncertainty_m = n900_uncertainty_m
    for track in gpx.tracks:
        for segment in track.segments:
            stops = stop_finder(segment.points, get_uncertainty_m)
            #save_stops(output, stop_finder(segment.points, get_uncertainty_m))
            save_simplified_stops(output, stops, get_uncertainty_m)
            #segment.points = replace_stops(stop_finder(segment.points, get_uncertainty_m), get_uncertainty_m)
#    print(gpx.to_xml(), file=output)
