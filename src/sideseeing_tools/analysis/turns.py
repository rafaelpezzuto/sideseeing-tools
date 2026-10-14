"""Gyroscope-based candidate turns; angles are in radians, not ground-truth labels."""

import numpy as np
import pandas as pd

from sideseeing_tools.analysis.timing import relative_signal, video_reference

WINDOW_S = 2.0
MIN_ANGLE_RAD = np.pi / 3
MERGE_GAP_S = 3.0
MAX_SAMPLE_GAP_S = 1.0
CONTEXT_S = 2.0
ALIGNMENT_TOLERANCE_S = 0.25
EVENT_COLUMNS = [
    'event_id',
    'event_start_s',
    'event_end_s',
    'start_s',
    'end_s',
    'angle_rad',
    'axis',
]


def detect_turns(
    gyroscope,
    axis,
    reference_time,
    duration_s,
    accelerometer=None,
    acceleration_limit=None,
    window_s=WINDOW_S,
    min_angle_rad=MIN_ANGLE_RAD,
    merge_gap_s=MERGE_GAP_S,
    max_sample_gap_s=MAX_SAMPLE_GAP_S,
    context_s=CONTEXT_S,
    alignment_tolerance_s=ALIGNMENT_TOLERANCE_S,
):
    """Integrate gyroscope rad/s over UTC-aligned windows on the selected device axis.

    Optional acceleration filtering uses m/s² with gravity; gaps break windows.
    Merge same-sign windows; angle_rad is the strongest window, not total rotation.
    """
    if axis not in ('x', 'y', 'z'):
        raise ValueError('axis must be x, y or z')

    parameters = dict(
        duration_s=duration_s,
        window_s=window_s,
        min_angle_rad=min_angle_rad,
        max_sample_gap_s=max_sample_gap_s,
    )

    if any(not np.isfinite(value) or value <= 0 for value in parameters.values()):
        raise ValueError('Duration, window, threshold and sample gap must be positive and finite')
    if any(
        not np.isfinite(value) or value < 0
        for value in (merge_gap_s, context_s, alignment_tolerance_s)
    ):
        raise ValueError(
            'Merge gap, context and alignment tolerance must be non-negative and finite'
        )

    times, values = relative_signal(gyroscope, [axis], reference_time)
    valid = (times >= 0) & (times <= duration_s)

    if acceleration_limit is not None:
        if accelerometer is None or not np.isfinite(acceleration_limit) or acceleration_limit <= 0:
            raise ValueError('Acceleration filtering requires a signal and a positive finite limit')

        acc_times, acc_values = relative_signal(accelerometer, ['x', 'y', 'z'], reference_time)

        if len(acc_times) == 0:
            valid[:] = False
        else:
            right = np.searchsorted(acc_times, times).clip(0, len(acc_times) - 1)
            left = (right - 1).clip(0, len(acc_times) - 1)
            nearest = np.where(
                abs(acc_times[left] - times) <= abs(acc_times[right] - times), left, right
            )
            valid &= abs(acc_times[nearest] - times) <= alignment_tolerance_s
            valid &= np.linalg.norm(acc_values[nearest], axis=1) <= acceleration_limit

    candidates = []
    # Split at missing/filtered samples and acquisition gaps before integration.
    indexes = np.flatnonzero(valid)
    breaks = (
        np.flatnonzero((np.diff(indexes) > 1) | (np.diff(times[indexes]) > max_sample_gap_s)) + 1
    )

    for segment_id, segment in enumerate(np.split(indexes, breaks)):
        if len(segment) < 2:
            continue

        t = times[segment]
        w = values[segment, 0]
        integral = np.r_[0, np.cumsum((w[:-1] + w[1:]) * np.diff(t) / 2)]
        ends = t + window_s

        for i in np.flatnonzero(ends <= t[-1]):
            angle = np.interp(ends[i], t, integral) - integral[i]

            if abs(angle) >= min_angle_rad:
                candidates.append([float(t[i]), float(ends[i]), float(angle), segment_id])

    merged = []

    for start, end, angle, segment_id in candidates:
        if (
            merged
            and segment_id == merged[-1][3]
            and start <= merged[-1][1] + merge_gap_s
            and np.sign(angle) == np.sign(merged[-1][2])
        ):
            merged[-1][1] = max(end, merged[-1][1])

            if abs(angle) > abs(merged[-1][2]):
                merged[-1][2] = angle
        else:
            merged.append([start, end, angle, segment_id])

    result = pd.DataFrame(
        [
            [
                i + 1,
                start,
                end,
                max(0, start - context_s),
                min(duration_s, end + context_s),
                angle,
                axis,
            ]
            for i, (start, end, angle, _) in enumerate(merged)
        ],
        columns=EVENT_COLUMNS,
    )
    result.attrs['parameters'] = dict(
        parameters,
        axis=axis,
        merge_gap_s=merge_gap_s,
        context_s=context_s,
        acceleration_limit=acceleration_limit,
        alignment_tolerance_s=alignment_tolerance_s,
    )
    result.attrs['reference_time'] = pd.to_datetime(reference_time, utc=True).isoformat()

    return result


def detect_instance_turns(instance, axis, gyroscope_name, accelerometer_name=None, **parameters):
    """Detect candidates from explicitly selected sensors in a SideSeeingInstance."""
    sensors = instance.sensors3 or {}

    if gyroscope_name not in sensors:
        raise ValueError(f'Gyroscope not found: {gyroscope_name}')
    if accelerometer_name is not None and accelerometer_name not in sensors:
        raise ValueError(f'Accelerometer not found: {accelerometer_name}')

    origin, duration = video_reference(instance)
    result = detect_turns(
        sensors[gyroscope_name],
        axis,
        origin,
        duration,
        accelerometer=sensors.get(accelerometer_name),
        **parameters,
    )
    result.attrs.update(
        source_id=instance.name,
        gyroscope_name=gyroscope_name,
        accelerometer_name=accelerometer_name,
    )

    return result
