import numpy as np
import pandas as pd

MEDIA_TIME_TOLERANCE_S = 0.05


def normalize_snippet_time_bounds(start_time, end_time):
    start_time = float(start_time)
    end_time = float(end_time)

    if not np.isfinite([start_time, end_time]).all() or start_time < 0:
        raise ValueError('Snippet bounds must be finite with a non-negative start')
    if end_time >= 0 and end_time <= start_time:
        raise ValueError('Snippet end must follow its start or be negative for the remaining video')

    if start_time.is_integer():
        start_time = int(start_time)
    if end_time.is_integer():
        end_time = int(end_time)

    return start_time, end_time


def extract_dataframe_snippet(
    data, start_time, end_time, output_path=None, reference_time=None, include_end=True
):
    """Select by shared UTC reference, or by per-series Time (s) when omitted."""
    if data.empty:
        print('ERROR. The input DataFrame is empty.')

        return None

    required_columns = ['Datetime UTC'] if reference_time is not None else ['Time (s)']

    for col in required_columns:
        if col not in data.columns:
            print(f"ERROR. Column '{col}' is not present in the DataFrame.")

            return None

    start_time, end_time = normalize_snippet_time_bounds(start_time, end_time)

    if reference_time is not None:
        timestamps = pd.to_datetime(data['Datetime UTC'], utc=True, errors='raise')

        if timestamps.isna().any():
            raise ValueError('Snippet timestamps must not be missing')

        origin = pd.to_datetime(reference_time, utc=True, errors='raise')

        if pd.isna(origin):
            raise ValueError('Snippet reference time must not be missing')

        times = (timestamps - origin).dt.total_seconds()
    else:
        times = data['Time (s)']

    if reference_time is None:
        if start_time < times.min():
            print('WARNING. The specified start time is before the data range.')
            start_time = times.min()

        if end_time > times.max() or end_time < 0:
            print('WARNING. The specified end time is after the data range.')
            end_time = times.max()

    within_end = times <= end_time if include_end else times < end_time
    snippet = data[(times >= start_time) & within_end]

    if output_path:
        snippet.to_csv(output_path, sep=',', columns=data.columns, index=False)

    return snippet


def resolve_snippet_time_bounds(start_time, end_time, duration):
    start_time, end_time = normalize_snippet_time_bounds(start_time, end_time)

    if not np.isfinite(duration) or duration <= 0:
        raise ValueError('Media duration must be positive and finite')
    if end_time < 0:
        end_time = duration
    if start_time >= duration or end_time > duration + MEDIA_TIME_TOLERANCE_S:
        raise ValueError('Snippet interval lies outside the recording')

    end_time = min(end_time, duration)

    return normalize_snippet_time_bounds(start_time, end_time)
