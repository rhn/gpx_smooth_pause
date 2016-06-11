import gpxpy


from device import n900_uncertainty_m, n900_m_to_dop

def fake_dop(points, get_uncertainty_m):
    for point in points:
        dop = n900_m_to_dop(get_uncertainty_m(point))
        point.horizontal_dilution = dop.horz
        point.vertical_dilution = dop.vert
        yield point

if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()
    with open(args.file) as infile:
        gpx = gpxpy.parse(infile)
    
    output = sys.stdout
    
    get_uncertainty_m = n900_uncertainty_m
    for track in gpx.tracks:
        for segment in track.segments:
            segment.points = fake_dop(segment.points, get_uncertainty_m)
    print(gpx.to_xml(), file=output)
