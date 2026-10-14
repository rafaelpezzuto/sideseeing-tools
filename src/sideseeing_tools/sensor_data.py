import datetime

import numpy as np
import pandas as pd

DEFAULT_TARGET_FPS = 30


def preprocess_sensors(
    data, num_axes, datetime_format, start_time=None, end_time=None, debug=False
):
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
            current_data.extend(
                [
                    float(row['axis_y']),
                    float(row['axis_z']),
                ]
            )

        if num_axes == 6:
            current_data.extend(
                [
                    float(row['delta_x']),
                    float(row['delta_y']),
                    float(row['delta_z']),
                ]
            )

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


def preprocess_consumption(data, datetime_format, start_time=None, end_time=None):
    rows = []

    for row in data:
        ts = datetime.datetime.strptime(row['datetime_utc'], datetime_format)

        if start_time is not None and ts < start_time:
            continue

        if end_time is not None and ts > end_time:
            continue

        rows.append([ts, float(row['battery_microamperes'])])

    sorted_rows = sorted(rows, key=lambda x: x[0])

    if not sorted_rows:
        return pd.DataFrame()

    return to_dataframe(sorted_rows, 1, datetime_format, data_type='consumption')


def preprocess_gps(data, datetime_format, start_time=None, end_time=None):
    rows = []

    for row in data:
        ts = datetime.datetime.strptime(row['datetime_utc'], datetime_format)

        if start_time is not None and ts < start_time:
            continue

        if end_time is not None and ts > end_time:
            continue

        rows.append(
            [ts]
            + [
                float(c)
                for c in [row['gps_interval'], row['accuracy'], row['latitude'], row['longitude']]
            ]
        )

    sorted_rows = sorted(rows, key=lambda x: x[0])

    if not sorted_rows:
        return pd.DataFrame()

    return to_dataframe(sorted_rows, 1, datetime_format, data_type='gps')


def to_dataframe(data, num_axes, datetime_format, data_type='sensor', create_time_column=True):
    """Build a modality DataFrame with optional elapsed seconds."""
    if not data:
        return pd.DataFrame()

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
        columns.extend(
            [
                'battery_microamperes',
            ]
        )

    elif data_type == 'gps':
        columns.extend(
            [
                'gps_interval',
                'accuracy',
                'latitude',
                'longitude',
            ]
        )

    elif data_type == 'wifi':
        columns.extend(['SSID', 'BSSID', 'level', 'frequency', 'standard'])

    elif data_type == 'cell':
        columns.extend(
            [
                'timestamp',
                'registered',
                'connection_status',
                'lac',
                'cid',
                'psc',
                'uarfcn',
                'mcc',
                'mnc',
                'ss',
                'alpha_long',
                'alpha_short',
                'ber',
                'rscp',
                'ecno',
                'level',
            ]
        )

    df = pd.DataFrame(data, columns=columns)

    if create_time_column:
        df['Datetime UTC'] = pd.to_datetime(df['Datetime UTC'], format=datetime_format)
        df['Time (s)'] = (df['Datetime UTC'] - df['Datetime UTC'].iloc[0]).dt.total_seconds()
        df = df.sort_values('Time (s)')

    return df


def resample_sensor_data(data, target_fps=DEFAULT_TARGET_FPS):
    """Select target_fps rows per populated second without changing timestamps.

    Skip empty seconds; repeat observed rows in sparse seconds.
    """
    if data.empty:
        return data.copy()

    samples = []

    for second in range(int(data['Time (s)'].max()) + 1):
        interval_start = second
        interval_end = second + 1

        selected_lines = data[
            (data['Time (s)'] >= interval_start) & (data['Time (s)'] < interval_end)
        ]

        if selected_lines.empty:
            continue

        indices = [
            int(x) for x in np.linspace(start=0, stop=len(selected_lines) - 1, num=target_fps)
        ]

        samples.append(selected_lines.iloc[indices])

    if not samples:
        return data.iloc[:0].copy()

    return pd.concat(samples, ignore_index=True)
