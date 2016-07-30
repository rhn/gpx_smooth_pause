# gps_smooth

This program smplifies GPX files by removing extra points where the track shows no movement.

## Description

gps_smooth detects stops in GPX files as the times when movement was less than current detector accuracy. It makes effort to never cut out real data: when movement begins again and exceeds the threshold, a few points immediately before are saved.

To estimate thresholds, the program needs to know the device accuracy - usually based on DOP value. Accuracy source can be customized: built-in support for Nokia N900 GPX files produced by [https://github.com/rhn/gpsrecorder-n900](https://github.com/rhn/gpsrecorder-n900).

## Requirements

* Python 3.4.3 (tested)
* gpxpy [https://github.com/tkrajina/gpxpy](https://github.com/tkrajina/gpxpy)

## Usage

To smooth a GPX file:

```
python3 smooth.py /foo.gpx > foo_simple.gpx
```

## Additional

The program contains an example DOP value faker for files that do not readily contain this value: `src/fakeDOP.py`.

The underlying model is concerned with movement periods and pause periods. While movement periods are always continuous, two disparate pause periods may come after one another, signifying separate pause positions.
It's possible to use the model to perform start/stop analysis, e.g. filter movement periods as separate tracks, strip pauses entirely or keep pauses only.
