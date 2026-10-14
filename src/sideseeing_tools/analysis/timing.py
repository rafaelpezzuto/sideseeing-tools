"""Validate timestamped signals for recording analyses."""

import numpy as np
import pandas as pd

from sideseeing_tools.metadata import recording_reference


def relative_signal(frame, columns, reference_time):
    required = ['Datetime UTC'] + columns

    if any(column not in frame for column in required):
        raise ValueError(f'Signal requires columns {required}')

    dates = pd.to_datetime(frame['Datetime UTC'], utc=True, errors='raise')
    times = (dates - pd.to_datetime(reference_time, utc=True)).dt.total_seconds().to_numpy()
    values = frame[columns].to_numpy(dtype=float)

    if not np.isfinite(times).all() or not np.isfinite(values).all():
        raise ValueError('Signal contains missing or non-finite values')
    if np.any(np.diff(times) <= 0):
        raise ValueError('Signal timestamps must be unique and increasing')

    return times, values


video_reference = recording_reference
