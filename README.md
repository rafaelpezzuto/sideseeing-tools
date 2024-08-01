# SideSeeing Tools

SideSeeing Tools is a collection of scripts designed to load, preprocess, and analyze data gathered through the MultiSensor Data Collection App.

## Installation

```bash
pip install sideseeing-tools
```


## Usage

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
#   .sensors    // Tip: lists the names of the available sensors
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

Running the command `extract_snippet` will generate one file for the video (with audio) and one file for each sensor present in the instance. See an illustrative example in the following file tree.

```text
home/
├─ user/
│  ├─ snippet_2_17/
│  │  ├─ accelerometer_2_12.csv
│  │  ├─ barometer_2_12.csv
│  │  ├─ gravity_2_12.csv
│  │  ├─ gyroscope_2_12.csv
│  │  ├─ gyroscope uncalibrated_2_12.csv
│  │  ├─ light uncalibrated_2_12.csv
│  │  ├─ linear accelerometer_2_12.csv
│  │  ├─ magnetometer_2_12.csv
│  │  ├─ magnetometer uncalibrated_2_12.csv
│  │  ├─ video_2_12.mp4
```

__Extract a snippet for a video__
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

__Extract a snippet for sensor data__
```python
from sideseeing_tools import utils

# Extract a 15-second snippet from the sensor data, beginning at the 3-second mark and ending at the 18-second mark
utils.extract_sensor_snippet(
    data=my_sample.sensors3['bmi160_accelerometer accelerometer non-wakeup'],  # DataFrame containing sensor data
    start_time=3,                                                              # Start time of the snippet (in seconds)
    end_time=18,                                                               # End time of the snippet (in seconds)
    output_path='my_sensor_snippet.csv'                                        # Path to save the extracted sensor snippet
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
#   .generate_video_sensor3()
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

## Sensor data specification before SideSeeing conversion

The following data outlines the specifications of sensor content before SideSeeing conversion, i.e., when accessing them directly through the files generated by the MultSensor Data Collection tool.


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
| `extract_snippet`     | Extracting a snippet from the sample (video and sensor data). |


## Author

[Rafael J P Damaceno](https://github.com/rafaelpezzuto)


## About us

The SideSeeing Project aims to develop methods based on Computer Vision and Machine Learning for Urban Informatics applications. Our goal is to devise strategies for obtaining and analyzing data related to urban accessibility. Take a look at our [website](https://sites.usp.br/sideseeing).
