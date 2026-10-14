import pandas as pd
import pytest

from sideseeing_tools.snippets import extract_dataframe_snippet

ORIGIN = '2024-03-09T18:59:08.770Z'


def test_shared_reference_excludes_gps_after_video_despite_series_time():
    gps = pd.DataFrame({'Datetime UTC': ['2024-03-09T18:59:35.723Z',
                                       '2024-03-09T18:59:49.292Z',
                                       '2024-03-09T19:00:05.904Z'],
                        'Time (s)': [0, 13.569, 30.181]})
    original = gps.copy(deep=True)

    selected = extract_dataframe_snippet(gps, 0, 40, reference_time=ORIGIN)

    assert selected.index.tolist() == [0]
    pd.testing.assert_frame_equal(gps, original)


def test_different_sensor_origins_share_same_utc_window():
    frame = pd.DataFrame({'Datetime UTC': ['2024-03-09T18:59:08.769Z',
                                         ORIGIN, '2024-03-09T18:59:48.770Z',
                                         '2024-03-09T18:59:48.771Z']})

    selected = extract_dataframe_snippet(frame, 0, 40, reference_time=ORIGIN)

    assert selected.index.tolist() == [1, 2]


def test_no_observations_in_window_returns_empty_without_moving_interval():
    frame = pd.DataFrame({'Datetime UTC': ['2024-03-09T19:00:05.904Z']})

    assert extract_dataframe_snippet(frame, 0, 40, reference_time=ORIGIN).empty


def test_invalid_utc_timestamps_are_rejected():
    frame = pd.DataFrame({'Datetime UTC': [None]})

    with pytest.raises(ValueError, match='missing'):
        extract_dataframe_snippet(frame, 0, 40, reference_time=ORIGIN)
