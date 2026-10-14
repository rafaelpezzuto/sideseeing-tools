import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from sideseeing_tools import metadata
from sideseeing_tools.analysis import turns, turn_snippets, timing

ORIGIN = pd.Timestamp('2024-01-01T00:00:00Z')


def signal(times, axis='z', value=1):
    frame = pd.DataFrame({'Datetime UTC': ORIGIN + pd.to_timedelta(times, unit='s'),
                          'x': 0., 'y': 0., 'z': 0.})
    frame[axis] = value
    return frame


def test_explicit_axis_and_context_bounds():
    frame = signal(np.arange(0, 5.1, .1))
    events = turns.detect_turns(frame, 'z', ORIGIN, 5, context_s=10)
    assert len(events) == 1
    assert events.iloc[0]['angle_rad'] == pytest.approx(2)
    assert events.iloc[0]['start_s'] == 0
    assert events.iloc[0]['end_s'] == 5
    assert turns.detect_turns(frame, 'x', ORIGIN, 5).empty


def test_unequal_rates_align_by_timestamp_and_reject_missing_acceleration():
    gyro = signal(np.arange(0, 5.1, .1))
    accel = signal(np.arange(0, 5.1, .5), value=9.8)
    events = turns.detect_turns(gyro, 'z', ORIGIN, 5, accelerometer=accel,
                                acceleration_limit=11, alignment_tolerance_s=.26)
    assert len(events) == 1
    accel['Datetime UTC'] += pd.Timedelta(seconds=10)
    assert turns.detect_turns(gyro, 'z', ORIGIN, 5, accelerometer=accel,
                              acceleration_limit=11).empty


def test_acquisition_gap_is_not_integrated_or_merged():
    frame = signal(np.r_[np.arange(0, 3.1, .1), np.arange(5, 8.1, .1)])
    events = turns.detect_turns(frame, 'z', ORIGIN, 9, merge_gap_s=10)
    assert len(events) == 2
    short = signal([0, .1, 5, 5.1])
    assert turns.detect_turns(short, 'z', ORIGIN, 6).empty


@pytest.mark.parametrize('times', [[0, 0, 1], [1, 0, 2]])
def test_invalid_timestamps_rejected(times):
    with pytest.raises(ValueError, match='unique and increasing'):
        turns.detect_turns(signal(times), 'z', ORIGIN, 5)


def test_empty_result_has_schema_and_nonfinite_rejected():
    assert list(turns.detect_turns(signal([]), 'z', ORIGIN, 5)) == turns.EVENT_COLUMNS
    frame = signal([0, 1, 2])
    frame.loc[1, 'z'] = np.nan
    with pytest.raises(ValueError, match='non-finite'):
        turns.detect_turns(frame, 'z', ORIGIN, 5)


def test_video_reference_includes_existing_crop(monkeypatch):
    class Capture:
        def __init__(self, path):
            pass
        def get(self, prop):
            return 20 if prop == metadata.cv2.CAP_PROP_FPS else 100
        def isOpened(self):
            return True
        def release(self):
            pass
    monkeypatch.setattr(metadata.cv2, 'VideoCapture', Capture)
    instance = SimpleNamespace(media_start_time=ORIGIN, video='video.mp4',
                               metadata={'snippet': {'start_time': 10, 'end_time': -1}})
    assert timing.video_reference(instance) == (ORIGIN + pd.Timedelta(seconds=10), 5)


def test_export_aligns_frames_preserves_source_and_identifies_recording(tmp_path, monkeypatch):
    metadata = {'time': {'videoStartDateTime': ORIGIN.isoformat()}}
    frame = signal([1, 2, 3, 4])
    frame['Time (s)'] = [0, 1, 2, 3]
    source = SimpleNamespace(name='route-B', metadata=metadata, sensors3={'gyro': frame})
    original = copy.deepcopy(metadata)
    events = turns.detect_turns(frame, 'z', ORIGIN, 5)
    events.attrs['source_id'] = source.name
    monkeypatch.setattr(turn_snippets, 'video_reference', lambda inst: (ORIGIN, 5))

    def extract(self, start, end, directory):
        Path(directory).mkdir()
        assert self.sensors3['gyro']['Time (s)'].tolist() == [0, 1, 2, 3]
        (Path(directory) / 'video.mp4').write_bytes(b'test')
    class Instance:
        extract_snippet = extract
    instance = Instance()
    instance.__dict__.update(source.__dict__)
    paths = turn_snippets.extract_turn_snippets(instance, events, tmp_path)
    assert paths[0] == tmp_path / 'route-B' / 'turn-0001'
    assert (paths[0] / 'turn.json').exists()
    assert instance.metadata == original
    assert frame['Time (s)'].tolist() == [0, 1, 2, 3]
    with pytest.raises(FileExistsError):
        turn_snippets.extract_turn_snippets(instance, events, tmp_path)
    events.attrs['source_id'] = 'route-A'
    with pytest.raises(ValueError, match='source'):
        turn_snippets.extract_turn_snippets(instance, events, tmp_path)


def test_opposite_rotations_do_not_merge():
    times = np.arange(0, 7.1, .1)
    frame = signal(times)
    frame.loc[times >= 3.5, 'z'] = -1
    events = turns.detect_turns(frame, 'z', ORIGIN, 8, merge_gap_s=10)
    assert len(events) == 2
    assert events.iloc[0]['angle_rad'] > 0
    assert events.iloc[1]['angle_rad'] < 0


def test_acceleration_above_limit_breaks_candidate_window():
    times = np.arange(0, 5.1, .1)
    gyro = signal(times)
    accel = signal(times, value=9.8)
    accel.loc[(times >= 1) & (times <= 4), 'z'] = 20
    assert turns.detect_turns(gyro, 'z', ORIGIN, 5, accelerometer=accel,
                              acceleration_limit=11).empty
