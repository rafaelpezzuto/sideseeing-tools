# SideSeeing Tools

SideSeeing Tools is a collection of scripts designed to load, preprocess, and analyze data gathered through the MultiSensor Data Collection App.

## Installation

```bash
pip install sideseeing-tools
```

## Usage

__Creating a dataset__
```python
from sideseeing_tools import sideseeing

ds = sideseeing.SideSeeingDS(root_dir='/home/user/my-project')

# Available iterators
#   .instances  // Tip: dictionary of instances (key=instance_name, value=SideSeeingInstance)
#   .iterator   // Tip: for i in ds.iterator: i.instance_name

# Available attributes and methods
#   .metadata() // Tip: generates and prints the dataset metadata
#   .size       // Tip: shows the number of instances  
#   .sensors    // Tip: lists the names of the available sensors
```

__Get a random sample from the dataset__
```python
my_sample = ds.instance
```

__Extract accelerometer data from the sample__
```python
my_accel_data = ds.instance['sensors3']['Accelerometer']
```

__Show available sensors in the dataset__
```python
ds.sensors
```

__Iterating over the samples__

```python
for i in ds.iterator:
    print(i.instance_name, i.video)
```

__Instance attributes (SideSeeingInstance)__

| Attribute or method | Description |
| ------------------- | ----------- |
| `geolocation_points`  | List of latitude and longitude coordinates representing geographical points. |
| `geolocation_center`  | Latitude and longitude coordinates representing the geographic center of a specific area. |
| `audio`               | Path to the audio file associated with the collected data. |
| `gif`                 | Path to the GIF file associated with the collected data. |
| `video`               | Path to the video file associated with the collected data. |
| `sensors1`            | Dictionary containing data from one-axis sensors. |
| `sensors3`            | Dictionary containing data from three-axis sensors. |
| `sensors6`            | Dictionary containing data from six-axis sensors, including uncalibrated data. |
| `label`               | List of categories and tags representing the taxonomy of sidewalks. |
| `video_start_time`    | Start time of the video associated with the collected data. |
| `video_stop_time`     | Stop time of the video associated with the collected data. |


__Creating a plotter__
```python
from sideseeing_tools import plot

plotter = plot.SideSeeingPlotter(ds, taxonomy='/home/user/my-project/taxonomy.csv')

# Available methods:
#   .plot_dataset_cities()
#   .plot_dataset_map()
#   .plot_dataset_sensors3()
#   .plot_dataset_tags_matrix()
#   .plot_dataset_tags()
#   .plot_instance_audio()
#   .plot_instance_map()
#   .plot_instance_sensors3_and_audio()
#   .plot_instance_video_frames_at_times()
#   .plot_instance_video_frames()
#   .generate_video_sensor3()
```

__Media tools__
```python
from sideseeing_tools import media

# Extract a 15-second snippet from the video, beginning at the 3-second mark and ending at the 18-second mark
media.extract_video_snippet(
    source_path=my_sample.video # Tip: path to a mp4 file
    start_second=3,
    end_second=18,
    output_path='my_snippet.mp4'
)
```

__Suggested dataset folder structure__

`ds = sideseeing.SideSeeingDS('/home/user/my-project', subdir='data', name='MyDataset')`

```text
my-project/
├─ data/
│  ├─ place01/
│  │  ├─ route01/
│  │  │  ├─ consumption.csv
│  │  │  ├─ gps.csv
│  │  │  ├─ metadata.json
│  │  │  ├─ sensors.one.csv
│  │  │  ├─ sensors.three.csv
│  │  │  ├─ sensors.three.uncalibrated.csv
│  │  │  ├─ video.gif
│  │  │  ├─ video.mp4
│  │  │  ├─ video.wav
│  │  ├─ route02/
│  ├─ place02/
│  ├─ place03/
├─ metadata.csv
├─ taxonomy.csv
```


## Sensors variables

### 3-axis sensors (accelerometer, gyroscope, among others)
| N | Column          | Description      |
|---|-----------------|----------------|
| 1 | timestamp_nano  | Timestamp in nanoseconds |
| 2 | datetime_utc    | Date/time in Coordinated Universal Time (UTC) |
| 3 | name            | Sensor name |
| 4 | axis_x          | Value of axis X |
| 5 | axis_y          | Value of axis Y |
| 6 | axis_z          | Value of axis Z |
| 7 | accuracy        | Sensor accuracy |


## Author

[Rafael J P Damaceno](https://github.com/rafaelpezzuto)


## About us

The SideSeeing Project aims to develop methods based on Computer Vision and Machine Learning for Urban Informatics applications. Our goal is to devise strategies for obtaining and analyzing data related to urban accessibility. Take a look at our [website](https://sites.usp.br/sideseeing).
