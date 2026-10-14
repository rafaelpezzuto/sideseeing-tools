# SideSeeing Tools

Python tools for loading, analyzing and visualizing recordings from the MultiSensor Data Collection App.

- Load recording directories and ZIP archives; access sensor, GPS, Wi-Fi and cellular data as pandas DataFrames.
- Extract video frames, crop recordings and split them into fixed-duration segments.
- Load video or audio-only recordings; generate plots and HTML reports.
- Detect candidate turns from gyroscope signals.
- Classify accelerometer activity and detect candidate pauses.
- Segment images with SAM3 and redact regions selected by masks.

## Installation

Python 3.9+ is required for the core package. Install the current checkout:

```bash
pip install -e .
```

Optional dependencies are installed separately:

```bash
pip install -e ".[har]"       # TensorFlow activity model and training tools
pip install -e ".[vision]"    # SAM3 segmentation
pip install -e ".[dev]"       # Tests
```

The published package is available with `pip install sideseeing-tools`.

## Load and inspect recordings

Each recording directory contains `metadata.json`, either `video.mp4` or an audio file
(`audio.m4a`, `*.audio.m4a` or `audio.wav`), and the available CSV files:
`consumption.csv`, `gps.csv`, `wifi.csv`, `cell.csv`, `sensors.one.csv`,
`sensors.three.csv` and `sensors.three.uncalibrated.csv`.

```python
from sideseeing_tools.sideseeing import SideSeeingDS

ds = SideSeeingDS(root_dir='./dataset', subdir_data='data')
instance = next(ds.iterator)
print(ds.size, ds.sensors)
print(instance.name, list(instance.sensors3 or {}))
```

`ds.instances` maps recording names to instances; `ds.iterator` iterates over them.
A ZIP file can also be passed as `root_dir`; ZIPs inside the data directory are
loaded automatically through temporary extraction.

An instance exposes `sensors1`, `sensors3` and `sensors6` dictionaries, plus
`geolocation_points`, `consumption`, `wifi_networks`, `cell_networks` and `label`.
Unavailable groups may be `None`. Use the exact sensor names reported by the dataset.

### Frames, snippets and plots

```python
from pathlib import Path

from sideseeing_tools.plot import SideSeeingPlotter

frames_dir = Path('./frames')
frames_dir.mkdir(exist_ok=True)
paths = instance.extract_frames_at_times([1.0], output_dir=str(frames_dir))
instance.extract_snippet(start_time=0, end_time=2, output_dir='./snippet')
SideSeeingPlotter(ds).plot_instance_map(instance)
```

Frame extraction returns images in memory when `output_dir` is omitted and requires video.
Snippets contain the video or audio, metadata and available sensor/network tables.
Use `end_time=-1` to keep the recording through its end. Export requires a new or
empty destination and preserves the original recording.
`extract_frames_at_positions`, `extract_frames_timespan` and
`extract_frames_positionspan` offer frame-number and interval selection.

### Automatic split and duration

```python
segments = instance.split(segment_duration=30, output_dir='./segments')
print(instance.media_total_time)
```

Split returns the generated directories in order, including the final shorter
segment. Video and audio-only recordings are supported. Each segment preserves
its UTC origin and sensor/network values; adjacent segments do not duplicate
boundary observations. Failed exports do not publish partial destinations.
`media_total_time` is the actual media-file duration in seconds.

## Motion analysis

### Turn detection

```python
from sideseeing_tools.analysis.turns import detect_instance_turns
from sideseeing_tools.analysis.turn_snippets import extract_turn_snippets

turns = detect_instance_turns(instance, axis='z', gyroscope_name='gyroscope')
extract_turn_snippets(instance, turns, './turn-snippets')
```

Replace `gyroscope` with the selected sensor name and choose the axis for the device
orientation. Input angular velocity is in rad/s. Results contain candidate and
context intervals relative to the recording, the strongest window angle and provenance.
The detector does not assign left/right labels. Export includes `turn.json` and
refuses existing snippet destinations.

### Activity classification and pause detection

```python
from sideseeing_tools.analysis.activity_models import load_activity_model
from sideseeing_tools.analysis.activity import classify_instance_activity
from sideseeing_tools.analysis.pauses import detect_pauses

model, parameters = load_activity_model()
activity = classify_instance_activity(
    instance, accelerometer_name='accelerometer', predict=model, **parameters,
)
pauses = detect_pauses(activity, min_duration_s=2)
```

Select acceleration including gravity in m/s² and replace the sensor name.
The bundled experimental model loads locally with the `har` extra and classifies
`stationary`, `walking` and `running`; low-confidence windows become `unknown`.
Use its returned preprocessing parameters. A custom model bundle or probability
predictor can also be supplied.

Pauses join consecutive stationary windows, stopping at gaps, motion or unknown
activity. Analyses align UTC timestamps to the media and avoid bridging acquisition
gaps. Turn and pause intervals are candidates requiring validation.

## Segmentation and redaction

```python
from sideseeing_tools.vision.segmentation import Sam3Segmenter
from sideseeing_tools.vision.results import save_segmentations, load_segmentation
from sideseeing_tools.privacy.redaction import save_redacted_image

segmenter = Sam3Segmenter()
records = segmenter.segment(paths, prompt='face')
manifest = save_segmentations(records, './face-results', source_id=instance.name)
result = load_segmentation(manifest, 0)
save_redacted_image(
    paths[0], result['masks'], './redacted/frame-0/image.png',
    mode='pixel', segmentation_provenance=result['metadata'],
)
```

SAM3 uses the `vision` extra and may download model weights on first use;
`Sam3Segmenter(local_files_only=True)` requires cached weights. Results preserve
instance masks, boxes, scores and source/model provenance. Stored results are
checked against their source and mask-file hashes when loaded.

Redaction accepts boolean masks at the source resolution, including manually
supplied masks through `redact_image`. Modes are `blur`, `pixel` and `solid`.
Only masked pixels change. File export writes a lossless PNG and `redaction.json`
into a new directory. Empty detections leave the image unchanged; outputs require
visual review for missed sensitive regions.

## HTML reports

```python
from sideseeing_tools.export import Report

Report().generate_report('./dataset/data', './report', title='Dataset report')
```

The report includes recording summaries, sensor charts, GPS routes and Wi-Fi maps.
Pass `segmentation_manifest` and matching `redaction_files` to include a redacted
image gallery. `viewer_url` links to a separate viewer. `anonymous=True` removes
project branding; it does not anonymize recording data.

Reports preserve source files by default. `generate_metadata=True` explicitly
requests a source `metadata.csv`. Analysis DataFrames retain provenance in `.attrs`;
CSV export does not preserve those attributes.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Tests use the local `src` directory. Run `tox` for the configured Python environments.
Activity-model training is available in [examples/train_activity_model.py](examples/train_activity_model.py).

Licensed under [MIT](LICENSE). Third-party model and dataset notices are retained
in [licenses](licenses/) and the bundled model directory.

Authors: [Rafael J. P. Damaceno](https://github.com/rafaelpezzuto) and
[Renzo Filho](https://github.com/Renzo-Filho).
