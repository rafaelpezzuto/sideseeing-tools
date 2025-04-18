# SideSeeing Tools

![Version](https://img.shields.io/badge/version-0.8.0-orange)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

SideSeeing Tools is a suite of scripts designed to load, preprocess, and analyze data collected using the MultiSensor Data Collection App. These tools facilitate the extraction and visualization of sensor data, making them valuable for urban informatics research and applications. This project is licensed under the MIT License, allowing for open-source distribution and modification. For more details, please refer to the [LICENSE](LICENSE) file.

SideSeeing Tools is compatible with Python version 3.9 and above. The tools are designed to work across multiple platforms, including Linux, macOS, and Windows. Here are some of the key features of SideSeeing Tools:

- **Data Loading**: Easily load data collected using the MultiSensor Data Collection App.
- **Preprocessing**: Preprocess the data to make it ready for analysis.
- **Analysis**: Perform various analyses on the data, including extracting and visualizing sensor data.
- **Visualization**: Generate visual representations of the data, such as plots and maps.
- **Frame Extraction**: Extract frames from video files at specified times or positions.
- **Snippet Extraction**: Extract snippets from video and sensor data for focused analysis.


## Installation

```bash
pip install sideseeing-tools
```


## General Usage

__Create a dataset__
```python
from sideseeing_tools import sideseeing

ds = sideseeing.SideSeeingDS(root_dir='/home/user/my-project')

# Available iterators
#   .instances  // Tip: dictionary of instances (key=name, value=SideSeeingInstance)
#   .iterator   // Tip: for i in ds.iterator: i.name

# Available attributes and methods
#   .metadata() // Tip: generates and prints the dataset metadata
#   .size       // Tip: shows the number of instances  
#   .sensors    // Tip: a dictionary containing the names of the available sensors
```

__Get a random sample from the dataset__
```python
my_sample = ds.instance
```

__Check the available sensors by instance__
```python
ds.sensors
# This command will produce output like this:

{
    # A key representing the number of available axes
    'sensors1': {
        # A key representing the sensor name
        'lps22h barometer sensor': {
            # Keys representing the instances where the sensor data is found
            'FhdFastest#S10e-2024-08-01-10-42-43-354',
            'FhdGame#S10e-2024-08-01-10-25-08-383',
            'FhdNormal#S10e-2024-08-01-10-02-18-947',
            'FhdUi#S10e-2024-08-01-10-13-50-369'
        },
        'tcs3407 uncalibrated lux sensor': {
            'FhdFastest#S10e-2024-08-01-10-42-43-354',
            ...
        },
        ...
    },
    'sensors3': {
        'ak09918c magnetic field sensor': {...},
        'bmi160_accelerometer accelerometer non-wakeup': {
            'FhdFastest#Mia3-2024-08-01-10-42-44-639',
            'FhdNormal#Mia3-2024-08-01-10-02-22-118',
            ...
        },
        ...
    },
    'sensors6': {
        ...
    }
}
```

__Get accelerometer data from the sample__
```python
my_sample = ds.instances['FhdNormal#Mia3-2024-08-01-10-02-22-118']
my_sample_accel_data = my_sample.sensors3['bmi160_accelerometer accelerometer non-wakeup']
my_sample_accel_data
```

|    | Datetime UTC               |       x |         y |       z |   Time (s) |
|---:|:---------------------------|--------:|----------:|--------:|-----------:|
|  0 | 2024-03-21 19:33:01.550000 | 9.34247 | -0.270545 | 3.10767 |      0     |
|  1 | 2024-03-21 19:33:01.561000 | 9.51725 | -0.347159 | 3.00233 |      0.011 |
|  2 | 2024-03-21 19:33:01.571000 | 9.46458 | -0.407014 | 2.81079 |      0.021 |
|  3 | 2024-03-21 19:33:01.581000 | 9.35205 | -0.395043 | 2.79164 |      0.031 |
|  4 | 2024-03-21 19:33:01.590000 | 9.36402 | -0.263362 | 2.77488 |      0.04  |


__Extract a snippet from a sample (video and sensor data)__
```python
my_sample.extract_snippet(
    start_time=2,                        # Start time of the snippet (in seconds)
    end_time=17,                         # End time of the snippet (in seconds)
    output_dir='/home/user/snippet_2_17' # Directory to save the extracted snippet
)
```

Running the command `extract_snippet` will generate one file for the video (with audio), one file for consumption data, one file for GPS data, and one file for each sensor type (single-axis, three-axis, three-axis uncalibrated) present in the instance. See an illustrative example in the following file tree.

```text
home/
├─ user/
│  ├─ snippet_2_17/
│  │  ├─ consumption.2_17.csv
│  │  ├─ gps.2_17.csv
│  │  ├─ sensors.one.2_17.csv
│  │  ├─ sensors.three.2_17.csv
│  │  ├─ sensors.three.uncalibrated.2_17.csv
│  │  ├─ video.2_17.mp4
```

__Extract only video snippets__

It is possible to extract a snippet from a video (and only the video) using the extract_video_snippet function.
```python
from sideseeing_tools import media

# Extract a 15-second snippet from the video, beginning at the 3-second mark and ending at the 18-second mark
media.extract_video_snippet(
    source_path=my_sample.video,    # Path to the input mp4 file
    start_second=3,                 # Start time of the snippet (in seconds)
    end_second=18,                  # End time of the snippet (in seconds)
    output_path='my_snippet.mp4'    # Path to save the extracted snippet
)
```

__Iterate over the samples__

```python
for i in ds.iterator:
    print(i.name, i.video)
```

__Create a plotter__
```python
from sideseeing_tools import plot

plotter = plot.SideSeeingPlotter(ds, taxonomy='/home/user/my-project/taxonomy.csv')

# Available methods:
#   .generate_video_for_sensor()
#   .plot_dataset_cities()
#   .plot_dataset_map()
#   .plot_dataset_tags_matrix()
#   .plot_dataset_tags()
#   .plot_instance_audio()
#   .plot_instance_map()
#   .plot_instance_sensors3_and_audio()
#   .plot_instance_video_frames_at_times()
#   .plot_instance_video_frames()
#   .plot_sensor()
#   .plot_sensors()
```

## Frame Extraction Methods

The following methods provide flexible and efficient ways to extract frames from video files, either saving them to disk or returning them in memory for immediate use in your applications. While using the methods below, you can opt for saving the frames to disk or returning them in memory.

__`extract_frames_at_times`__

This method extracts frames from a video file at the specified time points and saves them as image files.

**Parameters:**
- `source_path` (str): Path to the source video file.
- `frame_times` (list): List of time points (in seconds) at which frames should be extracted.
- `target_dir` (str, optional): Path to the target directory where frames will be saved. If `None`, frames will be returned in memory.
- `prefix` (str, optional): Prefix to be added to the frame file names.
- `left_zeros` (int, optional): Number of left-padded zeros in the frame file names.

**Returns:**
- `list`: List of paths to the extracted frames or list of frames in memory if `target_dir` is `None`.

__`extract_frames_at_positions`__

This method extracts frames from a video file at the specified frame positions and saves them as image files.

**Parameters:**
- `source_path` (str): Path to the source video file.
- `frame_positions` (list): List of frame positions at which frames should be extracted.
- `target_dir` (str, optional): Path to the target directory where frames will be saved. If `None`, frames will be returned in memory.
- `prefix` (str, optional): Prefix to be added to the frame file names.
- `left_zeros` (int, optional): Number of left-padded zeros in the frame file names.

**Returns:**
- `list`: List of paths to the extracted frames or list of frames in memory if `target_dir` is `None`.

__`extract_frames_timespan`__

This method extracts frames from a video file within a specified time span and saves them as image files.

**Parameters:**
- `source_path` (str): Path to the source video file.
- `start_time` (float): The start time (in seconds) of the time span from which frames should be extracted.
- `end_time` (float): The end time (in seconds) of the time span from which frames should be extracted.
- `target_dir` (str, optional): Path to the target directory where frames will be saved. If `None`, frames will be returned in memory.
- `step` (int, optional): The rate at which frames are extracted.
- `prefix` (str, optional): Prefix to be added to the frame file names.
- `left_zeros` (int, optional): Number of left-padded zeros in the frame file names.

**Returns:**
- `list`: List of paths to the extracted frames or list of frames in memory if `target_dir` is `None`.

__`extract_frames_positionspan`__

This method extracts frames from a video file within a specified position span and saves them as image files.

**Parameters:**
- `source_path` (str): Path to the source video file.
- `start_frame` (int): The start frame position from which frames should be extracted.
- `end_frame` (int): The end frame position from which frames should be extracted.
- `target_dir` (str, optional): Path to the target directory where frames will be saved. If `None`, frames will be returned in memory.
- `step` (int, optional): The rate at which frames are extracted.
- `prefix` (str, optional): Prefix to be added to the frame file names.
- `left_zeros` (int, optional): Number of left-padded zeros in the frame file names.

**Returns:**
- `list`: List of paths to the extracted frames or list of frames in memory if `target_dir` is `None`.

__`extract_frames`__

This method extracts frames from a video file at a specified frame rate and saves them as image files.

**Parameters:**
- `source_path` (str): Path to the source video file.
- `target_dir` (str, optional): Path to the target directory where frames will be saved. If `None`, frames will be returned in memory.
- `step` (int, optional): The rate at which frames are extracted.
- `prefix` (str, optional): Prefix to be added to the frame file names.
- `left_zeros` (int, optional): Number of left-padded zeros in the frame file names.

**Returns:**
- `list`: List of paths to the extracted frames or list of frames in memory if `target_dir` is `None`.

### Example Usage of Frame Extraction Methods through the `SideSeeingInstance`:

```python
from sideseeing_tools.sideseeing import SideSeeingDS

# Initialize the SideSeeingDS object
ds = sideseeing.SideSeeingDS(root_dir='/home/user/my-project')

# Get a random instance from the dataset
inst = ds.instance

# Extract frames at specific times and save to disk
inst.extract_frames_at_times(
    frame_times=[1.0, 2.0, 3.0],
    target_dir='output',
    prefix='frame_',
    left_zeros=5
)
```

### Example Usage of Frame Extraction Methods through the `media` module:

```python
from sideseeing_tools import media

# Extract frames at specific times and save to disk
media.extract_frames_at_times(
    source_path=video_path,
    frame_times=[1.0, 2.0, 3.0],
    target_dir='output',
    prefix='frame_',
    left_zeros=5
)

# Extract frames at specific times and return in memory
frames = media.extract_frames_at_times(
    source_path=video_path,
    frame_times=[1.0, 2.0, 3.0]
)

# Extract frames at specific positions and save to disk
media.extract_frames_at_positions(
    source_path=video_path,
    frame_positions=[30, 60, 90],
    target_dir='output',
    prefix='frame_',
    left_zeros=5
)

# Extract frames at specific positions and return in memory
frames = media.extract_frames_at_positions(
    source_path=video_path,
    frame_positions=[30, 60, 90]
)

# Extract frames within a timespan and save to disk
media.extract_frames_timespan(
    source_path=video_path,
    start_time=10.0,
    end_time=20.0,
    target_dir='output',
    step=30,
    prefix='frame_',
    left_zeros=5
)

# Extract frames within a timespan and return in memory
frames = media.extract_frames_timespan(
    source_path=video_path,
    start_time=10.0,
    end_time=20.0,
    step=30
)

# Extract frames within a position span and save to disk
media.extract_frames_positionspan(
    source_path=video_path,
    start_frame=300,
    end_frame=600,
    target_dir='output',
    step=30,
    prefix='frame_',
    left_zeros=5
)

# Extract frames within a position span and return in memory
frames = media.extract_frames_positionspan(
    source_path=video_path,
    start_frame=300,
    end_frame=600,
    step=30
)

# Extract frames at a specified frame rate and save to disk
media.extract_frames(
    source_path=video_path,
    target_dir='output',
    step=30,
    prefix='frame_',
    left_zeros=5
)

# Extract frames at a specified frame rate and return in memory
frames = media.extract_frames(
    source_path=video_path,
    step=30
)
```

## Additional tips

We suggest implementing the following folder structure: create a directory named `data` to contain all recordings. By doing so, when instantiating the `SideSeeingDataset`, a `metadata.csv` file will be generated in the root directory. Here is the command to instantiate a dataset:

```python
ds = sideseeing.SideSeeingDS('/home/user/my-project', subdir='data', name='MyDataset')
```

And here is the suggested folder structure:

```text
my-project/
├─ data/
│  ├─ place01/
│  │  ├─ route01/
|  |  |  ├─ cell.csv
│  │  │  ├─ consumption.csv
│  │  │  ├─ gps.csv
│  │  │  ├─ metadata.json
│  │  │  ├─ sensors.one.csv
│  │  │  ├─ sensors.three.csv
│  │  │  ├─ sensors.three.uncalibrated.csv
│  │  │  ├─ video.gif
│  │  │  ├─ video.mp4
│  │  │  ├─ video.wav
│  │  │  ├─ wifi.csv
│  │  ├─ route02/
│  ├─ place02/
│  ├─ place03/
├─ metadata.csv
├─ taxonomy.csv
```

## Sensor data specification before SideSeeing conversion

The following data outlines the specifications of sensor content before SideSeeing conversion, i.e., when accessing them directly through the files generated by the MultSensor Data Collection tool.

**File cell.csv**

| datetime_utc             | cellular_network |
|--------------------------|------------------|
| 2024-03-21T19:38:04.961Z | `data`           |


**File wifi.csv**

| datetime_utc              | wifi_network |
|---------------------------|--------------|
| 2024-03-21T19:38:04.961Z  | `data`       |


**File consumption.csv**

| datetime_utc             | battery_microamperes |
|--------------------------|----------------------|
| 2024-03-21T19:38:04.961Z | -1431                |
| 2024-03-21T19:38:05.961Z | -1011                |
| 2024-03-21T19:38:06.961Z | -2216                |

**File gps.csv**

| datetime_utc            | gps_interval | accuracy | latitude | longitude  |
|-------------------------|--------------|----------|----------|------------|
| 2024-03-21T19:38:10.309Z| 15           | 16.0     | -23.5645676 | -46.7395994 |
| 2024-03-21T19:38:38.033Z| 15           | 57.639   | -23.5645617 | -46.739602  |
| 2024-03-21T19:38:54.120Z| 15           | 26.611   | -23.5645528 | -46.7396658 |

**File sensors.one.csv**

| timestamp_nano       | datetime_utc            | name                        | axis_x           | accuracy  |
|----------------------|-------------------------|-----------------------------|------------------|-----------|
| 0                    | 2024-03-13T13:40:27.243Z| Palm Proximity Sensor       | 5.0              | 3         |
| 712657771915658      | 2024-03-21T19:38:05.015Z| TCS3407 Uncalibrated lux Sensor | 1810.0    | 3         |
| 712657931915658      | 2024-03-21T19:38:05.174Z| TCS3407 Uncalibrated lux Sensor | 1812.0    | 3         |

**File sensors.three.csv**

| timestamp_nano    | datetime_utc            | name                        | axis_x      | axis_y       | axis_z      | accuracy |
|-------------------|-------------------------|-----------------------------|-------------|--------------|-------------|----------|
| 712657652031560   | 2024-03-21T19:38:04.895Z| LSM6DSO Acceleration Sensor | 9.603442    | -0.10295067  | 3.9959226   | 3        |
| 712657673895658   | 2024-03-21T19:38:04.916Z| LSM6DSO Acceleration Sensor | 9.823709    | -0.38067806  | 3.9097314   | 3        |
| 712657652031560   | 2024-03-21T19:38:04.895Z| LSM6DSO Gyroscope Sensor    | 0.113544576 | 0.42852196   | 0.083306745 | 3        |

**File sensors.three.uncalibrated.csv**

| timestamp_nano    | datetime_utc            | name                            | axis_x       | axis_y        | axis_z       | delta_x        | delta_y       | delta_z       | accuracy |
|-------------------|-------------------------|---------------------------------|--------------|---------------|--------------|----------------|---------------|---------------|----------|
| 712657851915658   | 2024-03-21T19:38:05.094Z| Uncalibrated Magnetic Sensor   | 268.56       | -9.54         | -230.45999   | 255.48         | -2.28         | -227.94       | 3        |
| 712657852615658   | 2024-03-21T19:38:05.096Z| Gyroscope sensor UnCalibrated   | 0.044593163  | -0.13439035   | 0.07086037   | -0.003009122   | -0.016193425  | -0.0026664268| 3        |
| 712657862615658   | 2024-03-21T19:38:05.105Z| Gyroscope sensor UnCalibrated   | 0.042760566  | -0.05009095   | 0.100792766  | -0.003009122   | -0.016193425  | -0.0026664268| 3        |
| 712657874678965   | 2024-03-21T19:38:05.118Z| Uncalibrated Magnetic Sensor   | 268.62       | -8.639999     | -231.48      | 255.48         | -2.28         | -227.94       | 3        |
| 712657872615658   | 2024-03-21T19:38:05.116Z| Gyroscope sensor UnCalibrated   | 0.064751714  | -0.007330383  | 0.118507855  | -0.003009122   | -0.016193425  | -0.0026664268| 3        |


## List of `SideSeeingInstance` attributes/methods

| Attribute or method           | Description |
| ----------------------------- | ----------- |
| `geolocation_points`          | Dictionary containing geolocation data, including latitude and longitude coordinates representing geographical points. |
| `geolocation_center`          | Latitude and longitude coordinates representing the geographic center of a specific area. |
| `audio`                       | Path to the audio file associated with the collected data. |
| `cell_networks`               | Dictionary containing cellular network data. |
| `gif`                         | Path to the GIF file associated with the collected data. |
| `wifi_networks`               | Dictionary containing WiFi network data. |
| `video`                       | Path to the video file associated with the collected data. |
| `sensors1`                    | Dictionary containing data from one-axis sensors. |
| `sensors3`                    | Dictionary containing data from three-axis sensors. |
| `sensors6`                    | Dictionary containing data from six-axis sensors, including uncalibrated data. |
| `label`                       | List of categories and tags representing the taxonomy of sidewalks. |
| `video_start_time`            | Start time of the video associated with the collected data. |
| `video_stop_time`             | Stop time of the video associated with the collected data. |
| `extract_snippet`             | Extracting a snippet from the sample (video, sensor, gps and consumption data). |
| `extract_frames_at_times`     | Extract frames from a video file at specified time points and save them as image files. |
| `extract_frames_at_positions` | Extract frames from a video file at specified frame positions and save them as image files. |
| `extract_frames_timespan`     | Extract frames from a video file within a specified time span and save them as image files. |
| `extract_frames_positionspan` | Extract frames from a video file within a specified position span and save them as image files. |
| `extract_frames`              | Extract frames from a video file at a specified frame rate and save them as image files. |


## Author

[Rafael J P Damaceno](https://github.com/rafaelpezzuto)


## About us

The SideSeeing Project aims to develop methods based on Computer Vision and Machine Learning for Urban Informatics applications. Our goal is to devise strategies for obtaining and analyzing data related to urban accessibility. Take a look at our [website](https://sites.usp.br/sideseeing).
