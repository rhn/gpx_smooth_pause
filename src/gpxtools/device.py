from collections import namedtuple

Radius = namedtuple("Radius", ['horz', 'vert'])

N900_resolution = 6

def n900_uncertainty_m(point):
    hdopcm = point.extensions.get('hdopCM', None)
    if hdopcm is None:
        horz = None
    else:
        horz = float(hdopcm) / 100
    if point.elevation is None:
        vert = None
    else:
        vdopcm = point.extensions.get('vdopCM', None)
        if vdopcm is None:
            vert = None
        else:
            vert = float(vdopcm) / 100
    return Radius(horz, vert)

def n900_m_to_dop(radius):
    return Radius(horz=(None if radius.horz is None else radius.horz / N900_resolution),
                  vert=(None if radius.vert is None else radius.vert / N900_resolution))

