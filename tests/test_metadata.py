from unittest.mock import Mock
from types import SimpleNamespace

import cv2
import pytest

from sideseeing_tools import metadata


@pytest.mark.parametrize('fps,frames', [(0, 100), (float('inf'), 100), (25, 0), (25, float('nan'))])
def test_invalid_video_properties_raise_and_release_capture(monkeypatch, fps, frames):
    capture = Mock()
    capture.get.side_effect = lambda prop: {
        cv2.CAP_PROP_FPS: fps, cv2.CAP_PROP_FRAME_COUNT: frames,
        cv2.CAP_PROP_FRAME_WIDTH: 16, cv2.CAP_PROP_FRAME_HEIGHT: 12,
    }[prop]
    monkeypatch.setattr(metadata.cv2, 'VideoCapture', lambda path: capture)

    with pytest.raises(ValueError, match='video properties'):
        metadata.read_video_properties('invalid.mp4')

    capture.release.assert_called_once()


def test_metadata_generation_honors_custom_datetime_format(monkeypatch):
    instance = SimpleNamespace(name='recording', video='source.mp4', geolocation_center=None,
        metadata={'time': {'videoStartDateTime': '01/02/2024 03:04:05',
                           'videoStopDateTime': '01/02/2024 03:04:09'}})
    monkeypatch.setattr(metadata, 'read_video_properties',
                        lambda path: dict(frames=100, fps=25, width=16, height=12))

    row = metadata.generate_metadata(iter([instance]), '%d/%m/%Y %H:%M:%S').iloc[0]

    assert row['media_start_time'].month == 2
    assert row['media_start_time'].day == 1
    assert row['media_total_time'] == 4
