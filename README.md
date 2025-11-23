# SideSeeing Tools

![Version](https://img.shields.io/badge/version-0.10.0-orange)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

SideSeeing Tools is a suite of scripts designed to load, preprocess, and analyze data collected using the MultiSensor Data Collection App. These tools facilitate the extraction and visualization of sensor data, making them valuable for urban informatics research and applications.

This project is licensed under the MIT License. For more details, please refer to the [LICENSE](LICENSE) file.

## Table of Contents

- [Key Features](#key-features)
- [Installation](#installation)
- [General Usage](#general-usage)
  - [Create a Dataset](#create-a-dataset)
  - [Get a Random Sample](#get-a-random-sample)
  - [Check Available Sensors](#check-available-sensors)
  - [Get Sensor Data](#get-sensor-data)
  - [Extract a Snippet](#extract-a-snippet)
  - [Iterate Over Samples](#iterate-over-samples)
  - [Plotting Data](#plotting-data)
- [Frame Extraction](#frame-extraction)
  - [Frame Extraction Methods](#frame-extraction-methods)
  - [Example Usage](#example-usage-of-frame-extraction-methods)
- [Recommended Folder Structure](#recommended-folder-structure)
- [Sensor Data Specification](#sensor-data-specification)
- [SideSeeingInstance Attributes](#list-of-sideseeinginstance-attributesmethods)
- [Testing](#testing)
- [Contributing](#contributing)
- [Authors](#authors)
- [About Us](#about-us)

## Key Features

- **Data Loading**: Easily load data collected using the MultiSensor Data Collection App.
- **Preprocessing**: Preprocess the data to make it ready for analysis.
- **Analysis**: Perform various analyses on the data, including extracting and visualizing sensor data.
- **Visualization**: Generate visual representations of the data, such as plots and maps.
- **Report Generation**: Create comprehensive HTML reports from your dataset with summaries, maps, and interactive charts.
- **Frame Extraction**: Extract frames from video files at specified times or positions.
- **Snippet Extraction**: Extract snippets from video and sensor data for focused analysis.

## Installation

```bash
pip install sideseeing-tools
```

## General Usage

### Create a Dataset
```python
from sideseeing_tools import sideseeing

# It is recommended to follow the suggested folder structure
ds = sideseeing.SideSeeingDS(root_dir='./my-project', subdir='data', name='MyDataset')

# Available iterators
# ds.instances  -> Dictionary of instances (key=name, value=SideSeeingInstance)
# ds.iterator   -> Iterator for the instances

# Available attributes and methods
# ds.metadata() -> Generates and prints the dataset metadata
# ds.size       -> Shows the number of instances  
# ds.sensors    -> A dictionary containing the names of the available sensors
```

### Get a Random Sample
```python
# Get a random instance from the dataset
my_sample = ds.instance
print(f"Random sample: {my_sample.name}")
```

### Check Available Sensors
The `.sensors` attribute shows which sensors are available across all instances.
```python
# The output shows which instances have data for each sensor type
print(ds.sensors)
```
```json
{
    "sensors1": {
        "lps22h barometer sensor": {
            "FhdFastest#S10e-2024-08-01-10-42-43-354",
            "FhdGame#S10e-2024-08-01-10-25-08-383"
        }
    },
    "sensors3": {
        "ak09918c magnetic field sensor": { ... },
        "bmi160_accelerometer accelerometer non-wakeup": {
            "FhdFastest#Mia3-2024-08-01-10-42-44-639",
            "FhdNormal#Mia3-2024-08-01-10-02-22-118"
        }
    }
}
```

### Get Sensor Data
```python
# Get a specific instance
my_instance = ds.instances['FhdNormal#Mia3-2024-08-01-10-02-22-118']

# Get accelerometer data from the instance
accel_data = my_instance.sensors3['bmi160_accelerometer accelerometer non-wakeup']
print(accel_data.head())
```
|    | Datetime UTC               |       x |         y |       z |   Time (s) |
|---:|:---------------------------|--------:|----------:|--------:|-----------:|
|  0 | 2024-03-21 19:33:01.550000 | 9.34247 | -0.270545 | 3.10767 |      0     |
|  1 | 2024-03-21 19:33:01.561000 | 9.51725 | -0.347159 | 3.00233 |      0.011 |
|  2 | 2024-03-21 19:33:01.571000 | 9.46458 | -0.407014 | 2.81079 |      0.021 |

### Extract a Snippet
Extract a segment of video and sensor data.
```python
my_instance.extract_snippet(
    start_time=2,                        # Start time in seconds
    end_time=17,                         # End time in seconds
    output_dir='./my-snippet'            # Directory to save the snippet
)
```
This creates a directory `./my-snippet` with files for video, audio, and all sensor data for the specified time range.

### Iterate Over Samples
```python
for instance in ds.iterator:
    print(f"Instance: {instance.name}, Video Path: {instance.video}")
```

### Plotting Data
The `SideSeeingPlotter` offers various methods to visualize your data.
```python
from sideseeing_tools import plot

plotter = plot.SideSeeingPlotter(ds, taxonomy='./my-project/taxonomy.csv')

# Example: Plot a map of all instances in the dataset
plotter.plot_dataset_map()

# Example: Plot accelerometer and audio data for a specific instance
my_instance = ds.instances['FhdNormal#Mia3-2024-08-01-10-02-22-118']
plotter.plot_instance_sensors3_and_audio(
    instance=my_instance,
    sensor_name='bmi160_accelerometer accelerometer non-wakeup'
)
```

## Frame Extraction

You can extract frames from videos either directly through the `media` module or via a `SideSeeingInstance`. Frames can be saved to disk or returned in memory.

### Frame Extraction Methods
- `extract_frames_at_times`: Extracts frames at a list of specific timestamps (in seconds).
- `extract_frames_at_positions`: Extracts frames at a list of specific frame numbers.
- `extract_frames_timespan`: Extracts frames within a given start and end time.
- `extract_frames_positionspan`: Extracts frames within a given start and end frame number.
- `extract_frames`: Extracts all frames at a given rate (step).

### Example Usage of Frame Extraction Methods

#### Through a `SideSeeingInstance`
```python
# Get a random instance
inst = ds.instance

# Extract frames at 1.0, 2.0, and 3.0 seconds and save to 'output' directory
inst.extract_frames_at_times(
    frame_times=[1.0, 2.0, 3.0],
    target_dir='output',
    prefix='frame_'
)
```

#### Through the `media` module
```python
from sideseeing_tools import media

video_path = ds.instance.video

# Extract frames and return them as a list of images in memory
frames_in_memory = media.extract_frames_at_times(
    source_path=video_path,
    frame_times=[1.0, 2.0, 3.0]
)

# Extract frames from a time span and save to disk
media.extract_frames_timespan(
    source_path=video_path,
    start_time=10.0,
    end_time=20.0,
    target_dir='output',
    step=30  # Extract one frame every 30 frames
)
```

## Recommended Folder Structure

We suggest the following folder structure for your project. This allows `SideSeeingDS` to automatically generate a `metadata.csv` file in your project root.

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
│  │  │  ├─ video.mp4
│  │  │  ├─ ...
│  │  ├─ route02/
│  ├─ place02/
├─ metadata.csv
├─ taxonomy.csv
```

## Sensor Data Specification

This section details the data format as generated by the MultiSensor Data Collection tool, before conversion by SideSeeing.

<details>
<summary>Click to expand sensor data details</summary>

### File cell.csv
| datetime_utc             | cellular_network |
|--------------------------|------------------|
| 2025-11-09T10:24:24.476Z | `CellInfoWcdma:{...}` |

### File wifi.csv
| datetime_utc              | wifi_network |
|---------------------------|--------------|
| 2025-11-09T10:24:24.467Z  | `SSID: "Android123_6948", ...` |

### File consumption.csv
| datetime_utc             | battery_microamperes |
|--------------------------|----------------------|
| 2024-03-21T19:38:04.961Z | -1431                |

### File gps.csv
| datetime_utc            | gps_interval | accuracy | latitude | longitude  |
|-------------------------|--------------|----------|----------|------------|
| 2024-03-21T19:38:10.309Z| 15           | 16.0     | -23.5645676 | -46.7395994 |

### File sensors.one.csv
| timestamp_nano       | datetime_utc            | name                        | axis_x           | accuracy  |
|----------------------|-------------------------|-----------------------------|------------------|-----------|
| 712657771915658      | 2024-03-21T19:38:05.015Z| TCS3407 Uncalibrated lux Sensor | 1810.0    | 3         |

### File sensors.three.csv
| timestamp_nano    | datetime_utc            | name                        | axis_x      | axis_y       | axis_z      | accuracy |
|-------------------|-------------------------|-----------------------------|-------------|--------------|-------------|----------|
| 712657652031560   | 2024-03-21T19:38:04.895Z| LSM6DSO Acceleration Sensor | 9.603442    | -0.10295067  | 3.9959226   | 3        |

### File sensors.three.uncalibrated.csv
| timestamp_nano    | datetime_utc            | name                            | axis_x       | axis_y        | axis_z       | delta_x        | delta_y       | delta_z       | accuracy |
|-------------------|-------------------------|---------------------------------|--------------|---------------|--------------|----------------|---------------|---------------|----------|
| 712657852615658   | 2024-03-21T19:38:05.096Z| Gyroscope sensor UnCalibrated   | 0.044593163  | -0.13439035   | 0.07086037   | -0.003009122   | -0.016193425  | -0.0026664268| 3        |

</details>

## List of `SideSeeingInstance` attributes/methods

| Attribute/Method              | Description |
| ----------------------------- | ----------- |
| `geolocation_points`          | Geolocation data points. |
| `geolocation_center`          | Geographic center of the instance. |
| `audio`                       | Path to the audio file. |
| `video`                       | Path to the video file. |
| `gif`                         | Path to the GIF file. |
| `sensors1`, `sensors3`, `sensors6` | Dictionaries of sensor data. |
| `label`                       | Taxonomy tags for the instance. |
| `video_start_time`, `video_stop_time` | Video start and stop timestamps. |
| `extract_snippet()`           | Extracts a snippet of all data types. |
| `extract_frames_...()`        | Methods for frame extraction. |

## Testing

This project uses `tox` for managing test environments. Tests are located in the `tests/` directory.

To run the tests, execute the following command from the project root:
```bash
tox
```

## Contributing

Contributions are welcome! If you have a suggestion or find a bug, please open an issue to discuss it.

If you want to contribute with code, please fork the repository and submit a pull request.

## Authors

- [Rafael J P Damaceno](https://github.com/rafaelpezzuto)
- [Renzo Filho](https://github.com/Renzo-Filho)

## About Us

The SideSeeing Project aims to develop methods based on Computer Vision and Machine Learning for Urban Informatics applications. Our goal is to devise strategies for obtaining and analyzing data related to urban accessibility. Visit our [website](https://sites.usp.br/sideseeing) to learn more.
