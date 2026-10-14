from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from sideseeing_tools.analysis import activity
from sideseeing_tools.analysis.activity import classify_activity, classify_instance_activity
from sideseeing_tools.analysis.pauses import detect_pauses, PAUSE_COLUMNS

ORIGIN = pd.Timestamp('2024-01-01T00:00:00Z')


def signal(times, x=0, y=0, z=9.80665):
    return pd.DataFrame(dict(DatetimeUTC=ORIGIN + pd.to_timedelta(times, unit='s'),
                             x=x, y=y, z=z)).rename(columns={'DatetimeUTC': 'Datetime UTC'})


def stationary(windows):
    return np.tile([.95, .04, .01], (len(windows), 1))


def test_units_and_timestamp_grid_ignore_per_sensor_elapsed_origin():
    frame = signal(np.arange(0, 3.01, .01))
    frame['Time (s)'] = np.arange(len(frame)) + 50
    seen = []
    def predictor(windows):
        seen.append(windows)
        return stationary(windows)
    result = classify_activity(frame, predictor, ORIGIN, 3, 'fixture-model')
    assert seen[0].shape == (3, 26, 3)
    assert np.allclose(seen[0][:, :, 2], .25)
    assert np.allclose(seen[0][:, :, :2], 0)
    assert result.start_s.tolist() == [0, 1, 2]
    assert result.end_s.tolist() == [1, 2, 3]
    assert result.attrs['parameters']['model_id'] == 'fixture-model'


def test_time_interpolation_preserves_linear_signal_with_irregular_sampling():
    times = np.array([0, .08, .17, .26, .39, .51, .64, .78, .9, 1])
    seen = []
    def predictor(windows):
        seen.append(windows)
        return stationary(windows)
    classify_activity(signal(times, x=times * 9.80665), predictor, ORIGIN, 1, 'fixture')
    expected = np.arange(26) / 26 / 4
    assert np.allclose(seen[0][0, :, 0], expected)


def test_gaps_are_not_interpolated_or_joined_into_pause():
    times = np.r_[np.arange(0, 1.01, .01), np.arange(2, 3.01, .01)]
    result = classify_activity(signal(times), stationary, ORIGIN, 3, 'fixture')
    assert result.start_s.tolist() == [0, 2]
    assert detect_pauses(result).empty
    assert len(detect_pauses(result, min_duration_s=1)) == 2


def test_low_confidence_and_motion_break_stationary_intervals():
    predictions = np.array([[.95, .04, .01], [.94, .05, .01], [.4, .35, .25],
                            [.1, .85, .05], [.95, .04, .01], [.95, .04, .01]])
    activity = classify_activity(signal(np.arange(0, 6.01, .01)), lambda x: predictions,
                                  ORIGIN, 6, 'fixture')
    assert activity.label.tolist() == ['stationary', 'stationary', 'unknown', 'walking',
                                       'stationary', 'stationary']
    pauses = detect_pauses(activity)
    assert pauses[['start_s', 'end_s']].values.tolist() == [[0, 2], [4, 6]]
    assert pauses.minimum_confidence.tolist() == [.94, .95]
    assert pauses.attrs['status'] == 'candidate-not-validated'


def test_partial_windows_and_empty_data_do_not_call_model():
    def unexpected(windows):
        raise AssertionError('No complete observed windows')
    for frame in [signal([]), signal([0, .1, .2])]:
        result = classify_activity(frame, unexpected, ORIGIN, .5, 'fixture')
        assert result.empty
        assert list(detect_pauses(result)) == PAUSE_COLUMNS


@pytest.mark.parametrize('predictions', [np.array([[.5, .5]]), np.array([[1, 1, 1]]),
                                         np.array([[np.nan, 0, 1]])])
def test_bad_model_outputs_are_rejected(predictions):
    with pytest.raises(ValueError, match='Predictor'):
        classify_activity(signal(np.arange(0, 1.01, .01)), lambda x: predictions,
                           ORIGIN, 1, 'fixture')


def test_repeated_timestamps_are_rejected():
    with pytest.raises(ValueError, match='unique'):
        classify_activity(signal([0, 0, 1]), stationary, ORIGIN, 1, 'fixture')


def test_pause_windows_must_not_overlap():
    activity = pd.DataFrame(dict(start_s=[0, .5], end_s=[1, 1.5],
                                 label=['stationary'] * 2, confidence=[.9] * 2))
    with pytest.raises(ValueError, match='non-overlapping'):
        detect_pauses(activity)


def test_instance_classifier_shares_video_reference_and_source(monkeypatch):
    instance = SimpleNamespace(name='cropped', sensors3={'acc': signal(np.arange(0, 2.01, .01))})
    monkeypatch.setattr(activity, 'video_reference', lambda x: (ORIGIN, 2))
    result = classify_instance_activity(instance, 'acc', stationary, 'fixture')
    assert result.attrs['source_id'] == 'cropped'
    assert result.attrs['accelerometer_name'] == 'acc'
    with pytest.raises(ValueError, match='not found'):
        classify_instance_activity(instance, 'missing', stationary, 'fixture')


def test_window_centering_removes_constant_gravity_for_matching_model():
    seen = []
    def predictor(windows):
        seen.append(windows)
        return stationary(windows)
    frame = signal(np.arange(0, 2.01, .01), x=2, y=-3, z=9.2)
    result = classify_activity(frame, predictor, ORIGIN, 2, 'centered-fixture', center_window=True)
    assert np.allclose(seen[0], 0, atol=1e-7)
    assert result.attrs['parameters']['center_window'] is True
