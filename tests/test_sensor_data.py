import pandas as pd
import pytest

from sideseeing_tools.constants import DATETIME_UTC_FORMAT
from sideseeing_tools.sensor_data import preprocess_gps, resample_sensor_data


def test_gps_is_sorted_before_elapsed_time_origin_is_selected():
    rows = [dict(datetime_utc=f'2024-01-01T00:00:0{second}.000Z', gps_interval='1',
                 accuracy='1', latitude=str(second), longitude='0') for second in [2, 0, 1]]

    result = preprocess_gps(rows, DATETIME_UTC_FORMAT)

    assert result['Time (s)'].tolist() == [0, 1, 2]
    assert result['latitude'].tolist() == [0, 1, 2]


@pytest.mark.parametrize('times', [[0.1, 0.2, 2.1, 2.2], [2.1, 2.2, 4.1, 4.2]])
def test_resampling_skips_empty_seconds_without_filling_gaps(times):
    frame = pd.DataFrame({'Time (s)': times, 'x': [1, 2, 3, 4], 'name': ['sensor'] * 4})
    original = frame.copy(deep=True)

    result = resample_sensor_data(frame, target_fps=3)

    assert result['Time (s)'].tolist() == [times[0], times[0], times[1], times[2], times[2], times[3]]
    assert result['x'].tolist() == [1, 1, 2, 3, 3, 4]
    assert result['name'].tolist() == ['sensor'] * 6
    assert result.index.tolist() == list(range(6))
    pd.testing.assert_frame_equal(frame, original)


def test_resampling_empty_signal_preserves_schema():
    frame = pd.DataFrame({'Time (s)': pd.Series(dtype='float64'), 'x': pd.Series(dtype='float64'),
                          'name': pd.Series(dtype='object')})

    result = resample_sensor_data(frame)

    pd.testing.assert_frame_equal(result, frame)
