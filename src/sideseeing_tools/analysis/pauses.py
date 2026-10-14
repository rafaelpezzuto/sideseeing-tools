"""Candidate pauses derived from consecutive stationary activity predictions."""

import copy

import numpy as np
import pandas as pd

MIN_PAUSE_S = 2.0
TIME_TOLERANCE_S = 1e-9
PAUSE_COLUMNS = ['event_id', 'start_s', 'end_s', 'duration_s', 'minimum_confidence', 'windows']


def detect_pauses(activity, min_duration_s=MIN_PAUSE_S):
    """Merge adjacent stationary windows into candidate pause intervals.

    Gaps, unknown labels and motion break intervals; bounds retain window resolution.
    """
    if not np.isfinite(min_duration_s) or min_duration_s <= 0:
        raise ValueError('Minimum pause duration must be positive and finite')

    required = ['start_s', 'end_s', 'label', 'confidence']

    if any(column not in activity for column in required):
        raise ValueError(f'Activity requires columns {required}')

    values = activity[['start_s', 'end_s', 'confidence']].to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError('Activity contains non-finite bounds or confidence')
    if len(values) and (
        np.any(values[:, 0] < 0)
        or np.any(values[:, 1] <= values[:, 0])
        or np.any(values[:, 2] < 0)
        or np.any(values[:, 2] > 1)
    ):
        raise ValueError('Invalid activity bounds or confidence')
    if len(values) > 1 and np.any(values[1:, 0] < values[:-1, 1] - TIME_TOLERANCE_S):
        raise ValueError('Activity windows must be ordered and non-overlapping')
    if activity['label'].isna().any():
        raise ValueError('Activity labels must not be missing')

    intervals = []
    current = None

    for row in activity[required].itertuples(index=False, name=None):
        start, end, label, confidence = row

        if label == 'stationary':
            if current is not None and abs(start - current[1]) <= TIME_TOLERANCE_S:
                current[1] = end
                current[2] = min(current[2], confidence)
                current[3] += 1
            else:
                if current is not None:
                    intervals.append(current)

                current = [start, end, confidence, 1]
        elif current is not None:
            intervals.append(current)
            current = None

    if current is not None:
        intervals.append(current)

    rows = []

    for start, end, confidence, count in intervals:
        if end - start + TIME_TOLERANCE_S >= min_duration_s:
            rows.append([len(rows) + 1, start, end, end - start, confidence, count])

    result = pd.DataFrame(rows, columns=PAUSE_COLUMNS)
    result.attrs = copy.deepcopy(activity.attrs)
    result.attrs.update(
        method='stationary-activity-windows',
        min_pause_s=min_duration_s,
        status='candidate-not-validated',
    )

    return result
