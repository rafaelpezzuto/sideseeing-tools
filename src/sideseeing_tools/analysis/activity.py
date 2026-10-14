"""Time-based activity inference for a supplied accelerometer classifier."""

import numpy as np
import pandas as pd

from sideseeing_tools.analysis.timing import relative_signal, video_reference

LABELS = ('stationary', 'walking', 'running')
SAMPLE_RATE_HZ = 26
WINDOW_SAMPLES = 26
GRAVITY_M_S2 = 9.80665
TRAINING_SCALE_MG = 4000.0
MAX_SAMPLE_GAP_S = 0.25
MIN_CONFIDENCE = 0.8


def classify_activity(
    accelerometer,
    predict,
    reference_time,
    duration_s,
    model_id,
    sample_rate_hz=SAMPLE_RATE_HZ,
    window_samples=WINDOW_SAMPLES,
    labels=LABELS,
    normalization_scale_mg=TRAINING_SCALE_MG,
    max_sample_gap_s=MAX_SAMPLE_GAP_S,
    min_confidence=MIN_CONFIDENCE,
    center_window=False,
):
    """Classify non-overlapping xyz windows from acceleration in m/s² with gravity.

    Convert to milli-g and normalize; center only if training used centering.
    Interpolate within continuous segments; omit gaps and partial windows.
    Predictor shape: (windows, samples, 3) to (windows, classes).
    """
    if not callable(predict) or not isinstance(model_id, str) or not model_id.strip():
        raise ValueError('Supply a predictor and an explicit model identifier')
    if (
        not np.isfinite(duration_s)
        or duration_s <= 0
        or not np.isfinite(sample_rate_hz)
        or sample_rate_hz <= 0
        or not np.isfinite(normalization_scale_mg)
        or normalization_scale_mg <= 0
        or not np.isfinite(max_sample_gap_s)
        or max_sample_gap_s <= 0
    ):
        raise ValueError('Duration, rate, scale and gap must be positive and finite')
    if (
        isinstance(window_samples, bool)
        or not isinstance(window_samples, int)
        or window_samples < 2
    ):
        raise ValueError('Window samples must be an integer of at least two')
    if not isinstance(center_window, bool):
        raise ValueError('center_window must be boolean')

    labels = tuple(labels)

    if (
        not labels
        or len(set(labels)) != len(labels)
        or any(not isinstance(label, str) or not label or label == 'unknown' for label in labels)
    ):
        raise ValueError('Labels must be unique non-empty names, excluding unknown')
    if not np.isfinite(min_confidence) or not 0 <= min_confidence <= 1:
        raise ValueError('Confidence must be between zero and one')

    times, values = relative_signal(accelerometer, ['x', 'y', 'z'], reference_time)
    keep = (times >= 0) & (times <= duration_s)
    times, values = times[keep], values[keep]
    boundaries = np.flatnonzero(np.diff(times) > max_sample_gap_s) + 1
    windows, starts = [], []

    for indexes in np.split(np.arange(len(times)), boundaries):
        if len(indexes) < 2:
            continue

        t, xyz = times[indexes], values[indexes]
        first_tick = int(np.ceil(t[0] * sample_rate_hz))
        last_tick = int(np.floor(t[-1] * sample_rate_hz))

        for tick in range(first_tick, last_tick - window_samples + 1, window_samples):
            grid = (tick + np.arange(window_samples)) / sample_rate_hz
            interpolated = np.column_stack([np.interp(grid, t, xyz[:, axis]) for axis in range(3)])

            if center_window:
                interpolated = interpolated - interpolated.mean(axis=0, keepdims=True)

            normalized = interpolated * (1000 / GRAVITY_M_S2) / normalization_scale_mg
            windows.append(normalized)
            starts.append(tick / sample_rate_hz)

    columns = ['start_s', 'end_s', 'label', 'confidence'] + [
        f'probability_{label}' for label in labels
    ]
    rows = []

    if windows:
        probabilities = np.asarray(predict(np.asarray(windows)), dtype=float)

        if probabilities.shape != (len(windows), len(labels)):
            raise ValueError('Predictor output shape does not match windows and labels')
        if (
            not np.isfinite(probabilities).all()
            or np.any(probabilities < 0)
            or np.any(probabilities > 1)
            or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-5)
        ):
            raise ValueError('Predictor must return finite class probabilities summing to one')

        for start, probability in zip(starts, probabilities):
            index = int(np.argmax(probability))
            confidence = float(probability[index])
            label = labels[index] if confidence >= min_confidence else 'unknown'
            rows.append(
                [start, start + window_samples / sample_rate_hz, label, confidence, *probability]
            )

    result = pd.DataFrame(rows, columns=columns)
    result.attrs.update(
        reference_time=pd.to_datetime(reference_time, utc=True).isoformat(),
        parameters=dict(
            model_id=model_id,
            duration_s=float(duration_s),
            sample_rate_hz=sample_rate_hz,
            window_samples=window_samples,
            input_unit='m/s2',
            training_unit='mg',
            gravity_m_s2=GRAVITY_M_S2,
            normalization_scale_mg=normalization_scale_mg,
            max_sample_gap_s=max_sample_gap_s,
            min_confidence=min_confidence,
            center_window=center_window,
            labels=list(labels),
        ),
    )

    return result


def classify_instance_activity(instance, accelerometer_name, predict, model_id, **parameters):
    """Classify a recording using an explicitly selected accelerometer/model."""
    sensors = instance.sensors3 or {}

    if accelerometer_name not in sensors:
        raise ValueError(f'Accelerometer not found: {accelerometer_name}')

    origin, duration = video_reference(instance)
    result = classify_activity(
        sensors[accelerometer_name], predict, origin, duration, model_id, **parameters
    )
    result.attrs.update(source_id=instance.name, accelerometer_name=accelerometer_name)

    return result
