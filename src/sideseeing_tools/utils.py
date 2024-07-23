import csv
import datetime
import requests

import cv2
import numpy as np
import pandas as pd
import reverse_geocode


def load_csv_data(path: str, fieldnames: list, delimiter=','):
    '''
    Reads a CSV file using csv.DictReader and a predefined list of fields.
    '''
    data = []

    with open(path) as fin:
        for row in csv.DictReader(fin, fieldnames=fieldnames, delimiter=delimiter):
          new_row = {}
          for k, v in row.items():
            new_row[k.strip().lower()] = v.strip().lower()
          data.append(new_row)

    return data


def load_csv_data_with_pandas(path: str):
    return pd.read_csv(path)


def save_csv_data_with_pandas(data: pd.DataFrame, path: str, index=False):
    data.to_csv(path, index=index)


def generate_metadata(iterator, datetime_format: str):
    items = []

    for i in iterator:
        cap = cv2.VideoCapture(i.video)
        v_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        v_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        v_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        v_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        item = {}

        item['name'] = i.name
        item['geolocation_center'] = f'{i.geolocation_center[0]}, {i.geolocation_center[1]}'
        item['video_start_time'] = datetime.datetime.strptime(i.metadata.get('time', {}).get('videoStartDateTime', ''), datetime_format)
        item['video_end_time'] = datetime.datetime.strptime(i.metadata.get('time', {}).get('videoStopDateTime', ''), datetime_format)
        item['video_duration'] = round(v_frames / v_fps, 2)
        item['video_frames'] = v_frames
        item['video_fps'] = v_fps
        item['video_resolution'] = f'{v_width}x{v_height}'
        item['manufacturer'] = i.metadata.get('device', {}).get('manufacturer', '')
        item['model'] = i.metadata.get('device', {}).get('model', '')
        item['so_version'] = i.metadata.get('device', {}).get('androidVersion', '')
        
        items.append(item)

    return pd.DataFrame.from_dict(items)


def standardize_sensor_name(sensor_name: str):
  '''
  Obtains an adequately sensor's name
  '''
  sensor_name_lowered = sensor_name.lower()

  if 'accel' in sensor_name_lowered or 'acc' in sensor_name_lowered:
    if 'linear' in sensor_name_lowered:
      return 'Linear Accelerometer'
    return 'Accelerometer'

  if 'grav' in sensor_name_lowered:
    return 'Gravity'

  if 'gyro' in sensor_name_lowered:
    if 'uncali' in sensor_name_lowered:
       return 'Gyroscope Uncalibrated'
    return 'Gyroscope'

  if 'mag' in sensor_name_lowered:
    if 'uncali' in sensor_name_lowered:
       return 'Magnetometer Uncalibrated'
    return 'Magnetometer'

  if 'light' in sensor_name_lowered or 'lux' in sensor_name_lowered:
    if 'uncalibrated' in sensor_name_lowered:
      return 'Light Uncalibrated'
    return 'Light'

  if 'barome' in sensor_name_lowered:
    return 'Barometer'

  if 'proximity' in sensor_name_lowered:
    if 'non' in sensor_name_lowered:
      return 'Proximity Non-Wakeup'
    return 'Proximity'
  
  if 'pressure' in sensor_name_lowered:
    if 'non' in sensor_name_lowered:
      return 'Pressure Non-Wakeup'
    return 'Pressure'

  print(f'Unknown sensor {sensor_name} has been detected.')
  return sensor_name


def preprocess_sensors(data: dict, num_axes: int, datetime_format: str, start_time=None, end_time=None, debug=False):
  '''
  Converts the sensor data into appropriate data types and assigns time positions.
  '''
  series = {}
  ignored_lines = 0

  for row in data:
    ts = datetime.datetime.strptime(row['datetime_utc'], datetime_format)

    if start_time is not None and ts < start_time:
      ignored_lines += 1
      continue

    if end_time is not None and ts > end_time:
      ignored_lines += 1
      continue

    sensor_name = standardize_sensor_name(row['name'])
    if sensor_name not in series:
      series[sensor_name] = []

    current_data = [ts]

    if num_axes >= 1:
      current_data.append(float(row['axis_x']))

    if num_axes >= 3:
      current_data.extend([
        float(row['axis_y']),
        float(row['axis_z']),
      ])

    if num_axes == 6:
      current_data.extend([
        float(row['delta_x']),
        float(row['delta_y']),
        float(row['delta_z']),
      ])

    series[sensor_name].append(current_data)

  if ignored_lines > 0 and debug:
    print(f'INFO. {ignored_lines} lines has been ignored.')

  for key, value in series.items():
    series[key] = to_dataframe(value, num_axes, datetime_format)

  return series


def preprocess_gps(data: dict):
   return np.array([[float(d['latitude']), float(d['longitude'])] for d in data])


def to_dataframe(data: dict, num_axes: int, datetime_format: str, create_time_column=True):
  '''
  Converts data into a Pandas.DataFrame and includes a column to represent the duration in seconds of the time series
  '''
  columns = ['Datetime UTC']

  if num_axes >= 1:
    columns.append('x')

  if num_axes >= 3:
    columns.extend(['y', 'z'])

  if num_axes == 6:
    columns.extend(['dx', 'dy', 'dz'])

  df = pd.DataFrame(data, columns=columns)

  if create_time_column:
      df['Datetime UTC'] = pd.to_datetime(df['Datetime UTC'], format=datetime_format)
      df['Time (s)'] = (df['Datetime UTC'] - df['Datetime UTC'].iloc[0]).dt.total_seconds()
      df = df.sort_values('Time (s)')

  return df


def resample_sensor_data(data: pd.DataFrame, target_fps=30):
    '''
    Converts the sensor data to match the FPS rate of the video.
    This is necessary because the frequency of sensor data varies.
    At times, there are 100 points in a single second, while at other times, there are only 50 points.
    This variation is controlled by the Android device, and it is crucial to ensure synchronization between the video and sensor data.
    '''
    resampled_data = pd.DataFrame()

    for second in range(int(data['Time (s)'].max()) + 1):
        interval_start = second
        interval_end = second + 1

        selected_lines = data[(data['Time (s)'] >= interval_start) & (data['Time (s)'] < interval_end)]

        indices = [int(x) for x in np.linspace(
            start=0,
            stop=len(selected_lines) - 1,
            num=target_fps)
        ]

        sample = selected_lines.iloc[indices]
        resampled_data = pd.concat([resampled_data, sample])

    resampled_data.reset_index(drop=True, inplace=True)

    return resampled_data


def inverse_geocode(latitude: float, longitude: float, key: str=None):
    data = {'country': 'Unknown', 'city': 'Unknown'}

    if not key:
        geo = reverse_geocode.search([[latitude, longitude]])
        if geo:
            first_geo = geo.pop()
            data['country'] = first_geo.get('country', 'Unknown')
            data['city'] = first_geo.get('city', 'Unknown')
    else:
        data = inverse_geocode_from_google(latitude, longitude, key)

    return data


def inverse_geocode_from_google(latitude: float, longitude: float, key: str):
    response = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?latlng={float(latitude)},{float(longitude)}&location_type=ROOFTOP&result_type=street_address&key={key}').json()
    data = {'country': 'Unknown', 'city': 'Unknown'}

    for r in response.get("results"):
        for i in r.get('address_components'):
            if 'country' in i.get('types'):
                data['country'] = i.get('long_name')

            if 'administrative_area_level_2' in i.get('types'):
                data['city'] = i.get('long_name')

    return data


def extract_sensor_snippet(data: pd.DataFrame, start_time, end_time, output_path):
    if data.empty:
        print('ERROR. The input DataFrame is empty.')
        return None
    
    required_columns = ['Time (s)',]
    for col in required_columns:
        if col not in data.columns:
            print(f"ERROR. Column '{col}' is not present in the DataFrame.")
            return None
    
    if not ((start_time >= data['Time (s)'].min()) and (end_time <= data['Time (s)'].max())):
        print('ERROR. The specified time range is outside the data range.')
        return None
    
    snippet = data[(data['Time (s)'] >= start_time) & (data['Time (s)'] <= end_time)]
    
    snippet.to_csv(output_path, sep=',', columns=data.columns, index=False)
    
    return snippet
