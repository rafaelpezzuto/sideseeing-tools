"""Persist UTC-aligned sensor tables and metadata for recording snippets."""

import json
import os

import pandas as pd

from sideseeing_tools import constants, snippets

FRAME_CONFIGS = (
    (
        'geolocation_points',
        constants.GPS_FILE_NAME,
        constants.GPS_SNIPPET_FILE_NAME,
        constants.GPS_FILE_FIELDNAMES,
    ),
    (
        'consumption',
        constants.CONSUMPTION_FILE_NAME,
        constants.CONSUMPTION_SNIPPET_FILE_NAME,
        constants.CONSUMPTION_FILE_FIELDNAMES,
    ),
    (
        'cell_networks',
        constants.CELL_FILE_NAME,
        constants.CELL_SNIPPET_FILE_NAME,
        constants.CELL_SNIPPET_HEADER,
    ),
    (
        'wifi_networks',
        constants.WIFI_FILE_NAME,
        constants.WIFI_SNIPPET_FILE_NAME,
        constants.WIFI_SNIPPET_HEADER,
    ),
)
SENSOR_CONFIGS = (
    (
        'sensors1',
        constants.ONE_AXIS_FILE_NAME,
        constants.ONE_AXIS_SNIPPET_FILE_NAME,
        constants.ONE_AXIS_SENSORS_FILE_FIELDNAMES,
    ),
    (
        'sensors3',
        constants.THREE_AXES_FILE_NAME,
        constants.THREE_AXES_SNIPPET_FILE_NAME,
        constants.THREE_AXES_SENSORS_FILE_FIELDNAMES,
    ),
    (
        'sensors6',
        constants.THREE_AXES_UNCALIBRATED_FILE_NAME,
        constants.THREE_AXES_UNCALIBRATED_SNIPPET_FILE_NAME,
        constants.THREE_AXES_UNCALIBRATED_SENSORS_FILE_FIELDNAMES,
    ),
)
SENSOR_COLUMNS = {
    'Datetime UTC': 'datetime_utc',
    'x': 'axis_x',
    'y': 'axis_y',
    'z': 'axis_z',
    'dx': 'delta_x',
    'dy': 'delta_y',
    'dz': 'delta_z',
}


def write_frame_snippets(
    instance, start_time, end_time, output_dir, include_time_span_on_filename, reference_time
):
    for attribute, filename, timed_filename, fields in FRAME_CONFIGS:
        frame = getattr(instance, attribute, None)

        if frame is None or frame.empty:
            continue

        selected = snippets.extract_dataframe_snippet(
            frame, start_time, end_time, reference_time=reference_time, include_end=False
        )

        if selected.empty:
            continue

        if include_time_span_on_filename:
            filename = timed_filename.format(start_time, end_time)
        if attribute in ('geolocation_points', 'consumption'):
            selected = selected.rename(columns={'Datetime UTC': 'datetime_utc'})

        selected.to_csv(
            os.path.join(output_dir, filename),
            columns=fields,
            index=False,
            date_format=constants.DATETIME_UTC_FORMAT,
        )


def write_metadata_snippet(
    instance, start_time, end_time, output_dir, include_time_span_on_filename
):
    filename = constants.METADATA_FILE_NAME

    if include_time_span_on_filename:
        filename = constants.METADATA_SNIPPET_FILE_NAME.format(start_time, end_time)

    offset = instance.metadata.get('snippet', {}).get('start_time', 0)
    snippet_metadata = instance.metadata.copy()
    snippet_metadata['snippet'] = {
        'start_time': offset + start_time,
        'end_time': offset + end_time,
        'total_time': end_time - start_time,
    }

    with open(os.path.join(output_dir, filename), 'w') as stream:
        json.dump(snippet_metadata, stream, indent=4)


def write_sensors_snippet(
    instance, start_time, end_time, output_dir, include_time_span_on_filename, reference_time
):
    for attribute, filename, timed_filename, fields in SENSOR_CONFIGS:
        frames = []

        for sensor_name, frame in (getattr(instance, attribute, None) or {}).items():
            if frame.empty:
                continue

            selected = snippets.extract_dataframe_snippet(
                frame, start_time, end_time, reference_time=reference_time, include_end=False
            )

            if selected.empty:
                continue

            selected = selected.rename(columns=SENSOR_COLUMNS).copy()
            selected['name'] = sensor_name
            frames.append(selected)

        if not frames:
            continue

        if include_time_span_on_filename:
            filename = timed_filename.format(start_time, end_time)

        pd.concat(frames).to_csv(
            os.path.join(output_dir, filename),
            columns=fields,
            index=False,
            date_format=constants.DATETIME_UTC_FORMAT,
        )
