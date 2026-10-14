import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from sideseeing_tools import constants, media, metadata, snippet_export
from sideseeing_tools.analysis.activity import classify_instance_activity
from sideseeing_tools.analysis.pauses import detect_pauses
from sideseeing_tools.analysis.turn_snippets import extract_turn_snippets
from sideseeing_tools.export import Report
from sideseeing_tools.sideseeing import SideSeeingDS

FIXTURE = Path(__file__).parent.parent / 'fixtures/dataset/instance-001/video.mp4'
ORIGIN = pd.Timestamp('2024-01-01T00:00:00Z')


@pytest.fixture(scope='module')
def recording_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp('short-recording')
    media.extract_video_snippet(FIXTURE, 0, 5, folder / 'video.mp4')
    information = {'time': {'videoStartDateTime': ORIGIN.strftime(constants.DATETIME_UTC_FORMAT),
                            'videoStopDateTime': (ORIGIN + pd.Timedelta(seconds=5)).strftime(constants.DATETIME_UTC_FORMAT)}}
    (folder / 'metadata.json').write_text(json.dumps(information))
    return folder


@pytest.fixture
def recording(recording_folder):
    instance = next(SideSeeingDS(recording_folder).iterator)
    times = np.arange(0, 5.1, .5)
    frame = pd.DataFrame({'Datetime UTC': (ORIGIN + pd.to_timedelta(times, unit='s')).tz_localize(None),
                          'Time (s)': times, 'x': times + 1, 'y': times + 2, 'z': times + 3,
                          'dx': times + 10, 'dy': times + 20, 'dz': times + 30,
                          'timestamp_nano': np.arange(len(times)), 'accuracy': 3, 'name': 'sensor'})
    instance.sensors6 = {'sensor': frame}
    instance.sensors3 = {'accelerometer': frame.drop(columns=['dx', 'dy', 'dz'])}
    dates = [ORIGIN.tz_localize(None) + pd.Timedelta(seconds=.5)]
    instance.wifi_networks = pd.DataFrame({'Datetime UTC': dates, 'Time (s)': [.5],
        'SSID': ['A, "quoted" network'], 'BSSID': ['aa:bb:cc:dd:ee:ff'], 'level': ['-50'],
        'frequency': ['2400'], 'standard': ['11n']})
    row = {field: '' for field in constants.CELL_SNIPPET_HEADER}
    row.update({'Datetime UTC': dates[0], 'timestamp': 123456, 'registered': False,
                'mcc': 724, 'mnc': 5, 'alpha_long': 'Carrier, name', 'ss': -70, 'level': 3, 'Time (s)': .5})
    instance.cell_networks = pd.DataFrame([row])
    return instance


def test_negative_end_keeps_last_second_and_records_positive_duration(recording, tmp_path):
    destination = recording.extract_snippet(0, -1, tmp_path / 'remaining')
    instance = next(SideSeeingDS(destination).iterator)
    assert instance.media_total_time == pytest.approx(recording.media_total_time, abs=.04)
    assert instance.metadata['snippet']['end_time'] > 0
    assert instance.metadata['snippet']['total_time'] == pytest.approx(recording.media_total_time)


def test_nested_snippet_preserves_offset_and_utc_window(recording, tmp_path):
    first = next(SideSeeingDS(recording.extract_snippet(2, 4, tmp_path / 'first')).iterator)
    nested = next(SideSeeingDS(first.extract_snippet(.5, 1.5, tmp_path / 'nested')).iterator)
    origin, duration = metadata.recording_reference(nested)
    assert origin == ORIGIN + pd.Timedelta(seconds=2.5)
    assert duration == pytest.approx(1, abs=.04)
    assert nested.sensors6['sensor']['x'].tolist() == [3.5, 4]


def test_turn_export_from_existing_snippet_keeps_media_and_sensor_origin(recording, tmp_path):
    cropped = next(SideSeeingDS(recording.extract_snippet(2, 4, tmp_path / 'cropped')).iterator)
    origin, _ = metadata.recording_reference(cropped)
    events = pd.DataFrame({'event_id': [1], 'start_s': [.5], 'end_s': [1.5]})
    events.attrs.update(source_id=cropped.name, reference_time=origin.isoformat())

    paths = extract_turn_snippets(cropped, events, tmp_path / 'turns')

    exported = next(SideSeeingDS(paths[0]).iterator)
    assert metadata.recording_reference(exported)[0] == ORIGIN + pd.Timedelta(seconds=2.5)
    assert exported.sensors6['sensor']['x'].tolist() == [3.5, 4]


def test_snippet_roundtrip_preserves_biases_and_network_fields(recording, tmp_path):
    original = recording.sensors6['sensor'].copy(deep=True)
    instance = next(SideSeeingDS(recording.extract_snippet(0, 2, tmp_path / 'snippet')).iterator)
    for column in ['x', 'y', 'z', 'dx', 'dy', 'dz']:
        assert instance.sensors6['sensor'][column].tolist() == original.loc[original['Time (s)'] < 2, column].tolist()
    assert instance.wifi_networks['SSID'].tolist() == ['A, "quoted" network']
    assert instance.wifi_networks['level'].tolist() == ['-50']
    assert instance.cell_networks['alpha_long'].tolist() == ['Carrier, name']
    assert instance.cell_networks['registered'].tolist() == [False]
    assert instance.cell_networks['ss'].tolist() == [-70]
    pd.testing.assert_frame_equal(recording.sensors6['sensor'], original)


def test_fractional_timestamped_files_reload(recording, tmp_path):
    path = recording.extract_snippet(.5, 2.5, tmp_path / 'timestamped', include_time_span_on_filename=True)
    instance = next(SideSeeingDS(path).iterator)
    assert instance.video.endswith('video.0.5_2.5.mp4')
    assert instance.media_total_time == pytest.approx(2, abs=.04)
    assert 'sensor' in instance.sensors6


def test_split_keeps_final_remainder_without_duplicate_boundary_samples(recording, tmp_path):
    paths = recording.split(2, tmp_path / 'segments')
    instances = [next(SideSeeingDS(path).iterator) for path in paths]
    assert [instance.media_total_time for instance in instances] == pytest.approx([2, 2, 1], abs=.04)
    assert [metadata.recording_reference(instance)[0] for instance in instances] == [ORIGIN + pd.Timedelta(seconds=s) for s in [0, 2, 4]]
    timestamps = pd.concat([instance.sensors6['sensor']['Datetime UTC'] for instance in instances])
    assert timestamps.is_unique
    assert len(timestamps) == 10


def test_failed_media_export_does_not_publish_partial_files(recording, tmp_path):
    destination = tmp_path / 'failed'
    with patch('sideseeing_tools.media.extract_video_snippet', side_effect=OSError('encoder failed')):
        with pytest.raises(OSError, match='encoder failed'):
            recording.extract_snippet(0, 2, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob('.snippet-*'))


def test_split_failure_rolls_back_completed_segments(recording, tmp_path):
    export = media.extract_video_snippet
    calls = []

    def fail_second_segment(*arguments):
        calls.append(arguments)
        if len(calls) == 2:
            raise OSError('second segment failed')
        return export(*arguments)

    destination = tmp_path / 'failed-split'
    with patch('sideseeing_tools.media.extract_video_snippet', side_effect=fail_second_segment):
        with pytest.raises(OSError, match='second segment failed'):
            recording.split(2, destination)
    assert len(calls) == 2
    assert not destination.exists()
    assert not list(tmp_path.glob('.split-*'))


def test_existing_output_data_is_preserved(recording, tmp_path):
    destination = tmp_path / 'existing'
    destination.mkdir()
    marker = destination / 'keep.txt'
    marker.write_text('existing output')

    with pytest.raises(FileExistsError):
        recording.extract_snippet(0, 2, destination)
    with pytest.raises(FileExistsError):
        recording.split(2, destination)
    assert marker.read_text() == 'existing output'
    assert list(destination.iterdir()) == [marker]


def test_video_end_rounding_is_tolerated_but_large_overrun_is_rejected(recording, tmp_path):
    output = tmp_path / 'rounded.mp4'
    media.extract_video_snippet(recording.video, 4, 5.003, output)
    properties = metadata.read_video_properties(output)
    assert properties['frames'] / properties['fps'] == pytest.approx(1, abs=.04)
    with pytest.raises(ValueError, match='outside'):
        recording.extract_snippet(0, 6, tmp_path / 'outside')
    assert not (tmp_path / 'outside').exists()


@pytest.mark.parametrize('seconds', [0, -1, float('nan'), float('inf')])
def test_invalid_split_duration_does_not_create_outputs(recording, tmp_path, seconds):
    with pytest.raises(ValueError, match='Segment duration'):
        recording.split(seconds, tmp_path / 'invalid')
    assert not (tmp_path / 'invalid').exists()


def test_audio_only_load_duration_split_pauses_and_report(recording, tmp_path):
    folder = tmp_path / 'audio-only'
    folder.mkdir()
    media.extract_audio_snippet(recording.video, 0, 3, folder / 'recording.audio.m4a')
    information = {'time': {'mediaStartDateTime': ORIGIN.strftime(constants.DATETIME_UTC_FORMAT),
                            'mediaStopDateTime': (ORIGIN + pd.Timedelta(seconds=3)).strftime(constants.DATETIME_UTC_FORMAT)}}
    (folder / 'metadata.json').write_text(json.dumps(information))
    snippet_export.write_sensors_snippet(recording, 0, 3, folder, False, ORIGIN)
    instance = next(SideSeeingDS(folder).iterator)
    assert instance.video is None and instance.audio.endswith('recording.audio.m4a')
    assert instance.media_total_time == pytest.approx(3, abs=.05)
    rows = metadata.generate_metadata(iter([instance]), constants.DATETIME_UTC_FORMAT)
    assert rows.iloc[0]['media_type'] == 'audio'
    paths = instance.split(2, tmp_path / 'audio-segments')
    assert [next(SideSeeingDS(path).iterator).media_total_time for path in paths] == pytest.approx([2, 1], abs=.05)
    activity = classify_instance_activity(instance, 'accelerometer', lambda windows: np.tile([1, 0, 0], (len(windows), 1)),
                                         'test-model', sample_rate_hz=2, window_samples=2, max_sample_gap_s=1)
    assert not detect_pauses(activity, min_duration_s=1).empty
    events = pd.DataFrame({'event_id': [1], 'start_s': [.5], 'end_s': [1.5]})
    events.attrs.update(source_id=instance.name, reference_time=ORIGIN.isoformat())
    exported = next(SideSeeingDS(extract_turn_snippets(instance, events, tmp_path / 'audio-turns')[0]).iterator)
    assert exported.audio is not None and exported.video is None
    assert metadata.recording_reference(exported)[0] == ORIGIN + pd.Timedelta(seconds=.5)
    with pytest.raises(ValueError, match='requires a video'):
        instance.extract_frames_at_times([0])
    Report().generate_report(str(folder), str(tmp_path / 'audio-report'))
    assert (tmp_path / 'audio-report/index.html').is_file()
