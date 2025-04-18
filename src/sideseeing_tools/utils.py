import csv
import datetime
import re
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
        reader = csv.reader(fin, delimiter=delimiter)
        first_row = next(reader)
        
        if [field.strip().lower() for field in first_row] == [field.strip().lower() for field in fieldnames]:
            fin.seek(0)
            reader = csv.DictReader(fin, delimiter=delimiter)
        else:
            reader = csv.DictReader(fin, fieldnames=fieldnames, delimiter=delimiter)

        for row in reader:
            new_row = {k.strip().lower(): v.strip().lower() for k, v in row.items()}
            data.append(new_row)

    return data


def load_csv_data_with_pandas(path: str):
    return pd.read_csv(path)


def save_csv_data_with_pandas(data: pd.DataFrame, path: str, index=False):
    data.to_csv(path, index=index)


def extract_media_start_time(metadata: dict):
    video_start_time = metadata.get('time', {}).get('videoStartDateTime')
    media_start_time = metadata.get('time', {}).get('mediaStartDateTime')
    return video_start_time or media_start_time


def extract_media_stop_time(metadata: dict):
    video_stop_time = metadata.get('time', {}).get('videoStopDateTime')
    media_stop_time = metadata.get('time', {}).get('mediaStopDateTime')
    return video_stop_time or media_stop_time


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
        
        if hasattr(i, 'geolocation_center'):
          item['geolocation_center'] = f'{i.geolocation_center[0]}, {i.geolocation_center[1]}'
        else:
           item['geolocation_center'] = ''

        media_start_time = extract_media_start_time(i.metadata)
        media_stop_time = extract_media_stop_time(i.metadata)

        item['media_start_time'] = datetime.datetime.strptime(media_start_time, datetime_format)
        item['media_stop_time'] = datetime.datetime.strptime(media_stop_time, datetime_format)
        item['media_total_time'] = (item['media_stop_time'] - item['media_start_time']).total_seconds()

        item['video_frames'] = v_frames
        item['video_fps'] = v_fps
        item['video_resolution'] = f'{v_width}x{v_height}'

        item['manufacturer'] = i.metadata.get('device', {}).get('manufacturer', '')
        item['model'] = i.metadata.get('device', {}).get('model', '')
        item['so_version'] = i.metadata.get('device', {}).get('androidVersion', '')
        
        items.append(item)

    return pd.DataFrame.from_dict(items)


def preprocess_sensors(data: dict, num_axes: int, datetime_format: str, start_time=None, end_time=None, debug=False):
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

        sensor_name = row['name']

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

        current_data.append(row['timestamp_nano'])
        current_data.append(row['accuracy'])
        current_data.append(row['name'])

        series[sensor_name].append(current_data)

    if ignored_lines > 0 and debug:
        print(f'INFO. {ignored_lines} lines has been ignored.')

    for key, value in series.items():
        value.sort(key=lambda x: x[0])
        series[key] = to_dataframe(value, num_axes, datetime_format)

    return series


def preprocess_consumption(data: dict, datetime_format: str, start_time=None, end_time=None):
    rows = []
    ignored_lines = 0

    for row in data:
        ts = datetime.datetime.strptime(row['datetime_utc'], datetime_format)

        if start_time is not None and ts < start_time:
            ignored_lines += 1
            continue

        if end_time is not None and ts > end_time:
            ignored_lines += 1
            continue
        
        rows.append([ts, float(row['battery_microamperes'])])
    
    sorted_rows = sorted(rows, key=lambda x: x[0])

    if not sorted_rows:
        return pd.DataFrame()

    return to_dataframe(sorted_rows, 1, datetime_format, data_type='consumption')


def preprocess_gps(data: dict, datetime_format: str, start_time=None, end_time=None):
    rows = []
    ignored_lines = 0

    for row in data:
        ts = datetime.datetime.strptime(row['datetime_utc'], datetime_format)

        if start_time is not None and ts < start_time:
            ignored_lines += 1
            continue

        if end_time is not None and ts > end_time:
            ignored_lines += 1
            continue

        rows.append([ts] + [float(c) for c in [row['gps_interval'], row['accuracy'], row['latitude'], row['longitude']]])

    sorted_rows = sorted(rows, key=lambda x: x[0])

    if not sorted_rows:
        return pd.DataFrame()

    return to_dataframe(rows, 1, datetime_format, data_type='gps')


def process_cell_networks(path, datetime_format: str, start_time=None, end_time=None):
    data = []

    with open(path) as fin:
        next(fin)

        for line in fin:
            try:
                datetime_str, rest = line.strip().split(",", 1)
                ts = datetime.datetime.strptime(datetime_str, datetime_format)

                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue

                reg_match = re.search(r'mRegistered=(\w+)', rest)
                ci_match = re.search(r'mCi=(\d+)', rest)
                pci_match = re.search(r'mPci=(\d+)', rest)
                earfcn_match = re.search(r'mEarfcn=(\d+)', rest)
                rssi_match = re.search(r'rssi=(-?\d+)', rest)
                rsrp_match = re.search(r'rsrp=(-?\d+)', rest)
                rsrq_match = re.search(r'rsrq=(-?\d+)', rest)
                level_match = re.search(r'level=(\d+)', rest)

                row = {
                    'Datetime UTC': datetime_str,
                    'registered': reg_match.group(1) if reg_match else None,
                    'ci': ci_match.group(1) if ci_match else None,
                    'pci': pci_match.group(1) if pci_match else None,
                    'earfcn': earfcn_match.group(1) if earfcn_match else None,
                    'rssi': rssi_match.group(1) if rssi_match else None,
                    'rsrp': rsrp_match.group(1) if rsrp_match else None,
                    'rsrq': rsrq_match.group(1) if rsrq_match else None,
                    'level': level_match.group(1) if level_match else None
                }

                data.append(row)
            except Exception as e:
                print(f"Error processing line: {line.strip()}: {e}")
                continue

    return to_dataframe(data, 1, datetime_format, data_type='cell', create_time_column=True)


def process_wifi_networks(path, datetime_format: str, start_time=None, end_time=None):
    data = []

    with open(path) as fin:
        next(fin)

        for line in fin:
            try:
                datetime_str, rest = line.strip().split(",", 1)
                ts = datetime.datetime.strptime(datetime_str, datetime_format)

                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue

                ssid_match = re.search(r'SSID: "(.*?)"', rest)
                bssid_match = re.search(r'BSSID: ([0-9a-f:]{17})', rest)
                level_match = re.search(r'level: (-?\d+)', rest)
                freq_match = re.search(r'frequency: (\d+)', rest)
                standard_match = re.search(r'standard: (\w+)', rest)

                row = {
                    'Datetime UTC': datetime_str,
                    'SSID': ssid_match.group(1) if ssid_match else None,
                    'BSSID': bssid_match.group(1) if bssid_match else None,
                    'level': level_match.group(1) if level_match else None,
                    'frequency': freq_match.group(1) if freq_match else None,
                    'standard': standard_match.group(1) if standard_match else None
                }

                data.append(row)
            except Exception as e:
                print(f"Error processing line: {line.strip()}: {e}")
                continue

    return to_dataframe(data, 1, datetime_format, data_type='wifi', create_time_column=True)


def to_dataframe(data, num_axes: int, datetime_format: str, data_type='sensor', create_time_column=True):
    '''
    Converts data into a Pandas.DataFrame and includes a column to represent the duration in seconds of the time series.
    Also returns the count of data points for each sensor axis.
    '''
    columns = ['Datetime UTC']

    if data_type == 'sensor':
        if num_axes >= 1:
            columns.append('x')

        if num_axes >= 3:
            columns.extend(['y', 'z'])

        if num_axes == 6:
            columns.extend(['dx', 'dy', 'dz'])

        columns.extend(['timestamp_nano', 'accuracy', 'name'])

    elif data_type == 'consumption':
        columns.extend(['battery_microamperes',])

    elif data_type == 'gps':
        columns.extend(['gps_interval', 'accuracy', 'latitude', 'longitude',])

    elif data_type == 'wifi':
        columns.extend(['SSID', 'BSSID', 'level', 'frequency', 'standard'])

    elif data_type == 'cell':
        columns.extend(['registered', 'ci', 'pci', 'earfcn', 'rssi', 'rsrp', 'rsrq', 'level'])

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


def extract_dataframe_snippet(data: pd.DataFrame, start_time, end_time, output_path=None):
    if data.empty:
        print('ERROR. The input DataFrame is empty.')
        return None
    
    required_columns = ['Time (s)',]
    for col in required_columns:
        if col not in data.columns:
            print(f"ERROR. Column '{col}' is not present in the DataFrame.")
            return None
    
    if start_time < data['Time (s)'].min():
        print('WARNING. The specified start time is before the data range.')
        start_time = data['Time (s)'].min()

    if end_time > data['Time (s)'].max() or end_time < 0:
        print('WARNING. The specified end time is after the data range.')
        end_time = data['Time (s)'].max()
    
    snippet = data[(data['Time (s)'] >= start_time) & (data['Time (s)'] <= end_time)]
    
    if output_path:
        snippet.to_csv(output_path, sep=',', columns=data.columns, index=False)
    
    return snippet
