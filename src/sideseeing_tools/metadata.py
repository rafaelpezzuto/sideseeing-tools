from math import isfinite

import cv2
import pandas as pd
from moviepy import AudioFileClip

from sideseeing_tools.geolocation import inverse_geocode
from sideseeing_tools.formatting import format_location_to_string


def extract_media_start_time(metadata):
    video_start_time = metadata.get('time', {}).get('videoStartDateTime')
    media_start_time = metadata.get('time', {}).get('mediaStartDateTime')

    return video_start_time or media_start_time


def extract_media_stop_time(metadata):
    video_stop_time = metadata.get('time', {}).get('videoStopDateTime')
    media_stop_time = metadata.get('time', {}).get('mediaStopDateTime')

    return video_stop_time or media_stop_time


def read_video_properties(video_path):
    """Read finite video properties and always close the capture."""
    capture = cv2.VideoCapture(str(video_path))

    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if (
            not capture.isOpened()
            or not all(isfinite(value) for value in (fps, frames, width, height))
            or fps <= 0
            or frames <= 0
            or width <= 0
            or height <= 0
        ):
            raise ValueError('Cannot determine valid video properties')

        return dict(fps=fps, frames=int(frames), width=int(width), height=int(height))
    finally:
        capture.release()


def read_audio_properties(audio_path):
    with AudioFileClip(str(audio_path)) as clip:
        if not isfinite(clip.duration) or clip.duration <= 0:
            raise ValueError('Cannot determine valid audio duration')

        return dict(duration_s=clip.duration, sample_rate=clip.fps, channels=clip.nchannels)


def recording_reference(instance, datetime_format=None):
    origin = pd.to_datetime(
        extract_media_start_time(instance.metadata) or getattr(instance, 'media_start_time', None),
        utc=True,
        format=datetime_format,
    )
    offset = instance.metadata.get('snippet', {}).get('start_time', 0)

    if pd.isna(origin) or not isfinite(offset) or offset < 0:
        raise ValueError('Invalid recording time reference')
    if instance.video is not None:
        properties = read_video_properties(instance.video)
        duration = properties['frames'] / properties['fps']
    elif getattr(instance, 'audio', None) is not None:
        duration = read_audio_properties(instance.audio)['duration_s']
    else:
        raise ValueError('Recording has no video or audio')

    return origin + pd.to_timedelta(offset, unit='s'), duration


def generate_metadata(iterator, datetime_format, google_api_key=None):
    items = []

    for i in iterator:
        origin, duration = recording_reference(i, datetime_format=datetime_format)
        properties = read_video_properties(i.video) if i.video is not None else None

        item = {}

        item['name'] = i.name
        item['directory'] = i.metadata.get('directory', '')
        item['subdirectory'] = i.metadata.get('subdirectory', '')

        if getattr(i, 'geolocation_center', None):
            lat, lon = i.geolocation_center
            item['geolocation_center'] = f'{lat}, {lon}'

            location_data = inverse_geocode(lat, lon, key=google_api_key)
            item['location'] = format_location_to_string(location_data)
        else:
            item['geolocation_center'] = ''
            item['location'] = 'Unknown'

        item['media_start_time'] = origin
        item['media_stop_time'] = origin + pd.to_timedelta(duration, unit='s')
        item['media_total_time'] = duration
        item['media_type'] = 'video' if properties is not None else 'audio'

        item['video_frames'] = properties['frames'] if properties else 0
        item['video_fps'] = properties['fps'] if properties else 0
        item['video_resolution'] = (
            f"{properties['width']}x{properties['height']}" if properties else ''
        )

        item['manufacturer'] = i.metadata.get('device', {}).get('manufacturer', '')
        item['model'] = i.metadata.get('device', {}).get('model', '')
        item['so_version'] = i.metadata.get('device', {}).get('androidVersion', '')

        items.append(item)

    return pd.DataFrame.from_dict(items)
