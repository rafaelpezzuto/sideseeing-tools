import datetime
import json
import math
import os
import random
import re
import tempfile
from pathlib import Path

import pandas as pd

from sideseeing_tools import (
    archives,
    constants,
    exceptions,
    media,
    csv_io,
    geolocation,
    metadata,
    network_data,
    sensor_data,
    snippets,
    snippet_export,
)

SNIPPET_SUFFIX_PATTERN = r'\.-?\d+(?:\.\d+)?_-?\d+(?:\.\d+)?(?=\.(?:csv|json|mp4|wav|m4a)$)'


class SideSeeingDS:
    def __init__(
        self,
        root_dir,
        subdir_data='.',
        name='MyDataset',
        generate_metadata=False,
        extract_media=False,
        google_api_key=None,
    ):
        print('INFO. Loading data.')
        self.name = name

        root_dir = os.fsdecode(os.fspath(root_dir))
        subdir_data = os.fsdecode(os.fspath(subdir_data))
        self._temporary_data = None

        if os.path.isfile(root_dir) and root_dir.lower().endswith('.zip'):
            self.root_dir = root_dir
            self._metadata_path = f'{os.path.splitext(root_dir)[0]}.metadata.csv'
            self.data_dir = self._create_temporary_data_dir()
            archives.extract_dataset_archive(root_dir, self.data_dir)
            self._data_dirs = [self.data_dir]
        elif os.path.isdir(root_dir):
            self.root_dir = (
                root_dir if root_dir.endswith(os.path.sep) else f'{root_dir}{os.path.sep}'
            )
            self._metadata_path = os.path.join(self.root_dir, 'metadata.csv')
            self.data_dir = os.path.join(self.root_dir, subdir_data)
            self._data_dirs = [self.data_dir]
            self._include_archived_data()
        else:
            raise exceptions.RootDirIsNotADirectoryError()

        self.setup(extract_media)

        if generate_metadata:
            self.metadata(generate_metadata, google_api_key)

        print('INFO. Done.')

    def _create_temporary_data_dir(self):
        if self._temporary_data is None:
            self._temporary_data = tempfile.TemporaryDirectory(prefix='sideseeing-tools-')

        return self._temporary_data.name

    def _include_archived_data(self):
        archive_paths = archives.find_zip_archives(self.data_dir)

        if not archive_paths:
            return

        temporary_dir = self._create_temporary_data_dir()
        archives.extract_dataset_archives(self.data_dir, temporary_dir, archive_paths)

        self._data_dirs.append(temporary_dir)

    def setup(self, extract_media):
        self.instances = {}
        invalid_instances = []

        for data_dir in self._data_dirs:
            for root, _, files in os.walk(data_dir):
                for f in files:
                    ssf = SideSeeingFile(data_dir, os.path.join(root, f))

                    if ssf.is_valid:
                        if ssf.name not in self.instances:
                            self.instances[ssf.name] = SideSeeingInstance(ssf.name, ssf.path)
                            self.instances[ssf.name]._temporary_data = self._temporary_data
                        elif os.path.realpath(self.instances[ssf.name].path) != os.path.realpath(
                            ssf.path
                        ):
                            raise ValueError(f'Duplicate recording identifier: {ssf.name}')

                        self.instances[ssf.name].add_file(ssf)

        for key in self.instances.keys():
            is_valid_instance = self.instances[key].setup(extract_media)

            if not is_valid_instance:
                invalid_instances.append(key)

        for key in invalid_instances:
            self.instances.pop(key)

        self.populate_sensors()

    def populate_sensors(self):
        self.sensors = {
            'sensors1': {},
            'sensors3': {},
            'sensors6': {},
        }

        for instance in self.iterator:
            for n_axis in self.sensors.keys():
                sensor_dict = getattr(instance, n_axis, None)

                if sensor_dict is not None:
                    for name in sensor_dict.keys():
                        if name not in self.sensors[n_axis]:
                            self.sensors[n_axis][name] = set()

                        self.sensors[n_axis][name].add(instance.name)

    @property
    def instance(self):
        return self.instances[random.choice(list(self.instances.keys()))]

    @property
    def size(self):
        return len(self.instances)

    @property
    def iterator(self):
        for k in sorted(self.instances.keys()):
            yield self.instances[k]

    def metadata(self, save=False, google_api_key=None):
        if self.size == 0:
            print(f'ERROR. Dataset is empty.')

            return

        path = self._metadata_path

        if os.path.exists(path) and not save:
            df = csv_io.load_csv_data_with_pandas(path)

        if not os.path.exists(path) or save:
            df = metadata.generate_metadata(
                self.iterator, constants.DATETIME_UTC_FORMAT, google_api_key
            )
            csv_io.save_csv_data_with_pandas(df, path)

        return df

    def __str__(self):
        return f'SSDS[name: {self.name}, instances: {self.size}]'

    def __repr__(self):
        return self.__str__()


class SideSeeingFile:
    def __init__(self, data_dir, path):
        self.data_dir = data_dir
        self.file_path = path
        self.setup()

    def setup(self):
        self.file_name = os.path.basename(self.file_path)
        self.file_type = self._discover_file_type()
        self.path = os.path.dirname(self.file_path)
        self.name = self._gen_instance_name(self.file_path, self.data_dir)
        self.is_valid = False if self.file_type == 'unknown' else True

    def _gen_instance_name(self, file_path, data_dir):
        instance_dir = os.path.dirname(file_path)
        relative_dir = os.path.relpath(instance_dir, data_dir)

        if relative_dir == os.curdir:
            return os.path.basename(os.path.normpath(data_dir))

        return '_'.join(relative_dir.split(os.path.sep))

    def _discover_file_type(self):
        filename = re.sub(SNIPPET_SUFFIX_PATTERN, '', self.file_name)

        if filename in constants.FILE_TYPES:
            return constants.FILE_TYPES[filename]
        if filename.endswith('.audio.m4a'):
            return 'audio'

        return 'unknown'

    def __str__(self):
        return f'SSFile[file_path: {self.file_path}]'

    def __repr__(self):
        return self.__str__()


class SideSeeingInstance:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.files = {}

    def add_file(self, ssf):
        self.files[ssf.file_type] = ssf

    def __str__(self):
        return f'SSInstance[name: {self.name}]'

    def __repr__(self):
        return self.__str__()

    def print_metadata(self):
        print(f"----\nName: {self.name}")
        print(
            f"Path: {self.path}",
            f"Manufacturer: {self.metadata.get('device', {}).get('manufacturer', '').title()}",
            f"Model: {self.metadata.get('device', {}).get('model', '')}",
            f"Android version: {self.metadata.get('device', {}).get('androidVersion', '')}",
            f"Media start time: {self.media_start_time}",
            f"Media stop time: {self.media_stop_time}",
            f"Media total time: {self.media_total_time}",
            sep='\n',
        )

    def setup(self, extract_media=False):
        try:
            with open(self.files['metadata'].file_path) as json_file:
                self.metadata = json.load(json_file)
        except KeyError:
            return False

        if self.metadata is None:
            return False

        media_start_time = metadata.extract_media_start_time(self.metadata)
        media_stop_time = metadata.extract_media_stop_time(self.metadata)

        self.media_start_time = datetime.datetime.strptime(
            media_start_time, constants.DATETIME_UTC_FORMAT
        )
        self.media_stop_time = datetime.datetime.strptime(
            media_stop_time, constants.DATETIME_UTC_FORMAT
        )
        self.media_total_time = (self.media_stop_time - self.media_start_time).total_seconds()

        attributes = [
            'consumption',
            'geolocation_points',
            'geolocation_center',
            'sensors3',
            'sensors6',
            'sensors1',
            'cell_networks',
            'wifi_networks',
            'label',
            'video',
            'audio',
            'gif',
        ]

        for attr in attributes:
            setattr(self, attr, None)

        for file_type in ('video', 'audio', 'gif'):
            if file_type in self.files:
                setattr(self, file_type, self.files[file_type].file_path)

        if self.video is not None or self.audio is not None:
            _, self.media_total_time = metadata.recording_reference(self)

        for k, v in self.files.items():
            if k == 'consumption':
                self.consumption = sensor_data.preprocess_consumption(
                    csv_io.load_csv_data(
                        v.file_path, fieldnames=constants.CONSUMPTION_FILE_FIELDNAMES
                    ),
                    constants.DATETIME_UTC_FORMAT,
                    self.media_start_time,
                    self.media_stop_time,
                )

            if k == 'gps':
                self.geolocation_points = sensor_data.preprocess_gps(
                    csv_io.load_csv_data(v.file_path, fieldnames=constants.GPS_FILE_FIELDNAMES),
                    constants.DATETIME_UTC_FORMAT,
                    self.media_start_time,
                    self.media_stop_time,
                )

                if not self.geolocation_points.empty:
                    self.geolocation_center = (
                        self.geolocation_points[['latitude', 'longitude']].mean().tolist()
                    )
                else:
                    self.geolocation_center = None

            if k == 'sensors3':
                self.sensors3 = sensor_data.preprocess_sensors(
                    csv_io.load_csv_data(
                        v.file_path, fieldnames=constants.THREE_AXES_SENSORS_FILE_FIELDNAMES
                    ),
                    3,
                    constants.DATETIME_UTC_FORMAT,
                    self.media_start_time,
                    self.media_stop_time,
                )

            if k == 'sensors6':
                self.sensors6 = sensor_data.preprocess_sensors(
                    csv_io.load_csv_data(
                        v.file_path,
                        fieldnames=constants.THREE_AXES_UNCALIBRATED_SENSORS_FILE_FIELDNAMES,
                    ),
                    6,
                    constants.DATETIME_UTC_FORMAT,
                    self.media_start_time,
                    self.media_stop_time,
                )

            if k == 'sensors1':
                self.sensors1 = sensor_data.preprocess_sensors(
                    csv_io.load_csv_data(
                        v.file_path, fieldnames=constants.ONE_AXIS_SENSORS_FILE_FIELDNAMES
                    ),
                    1,
                    constants.DATETIME_UTC_FORMAT,
                    self.media_start_time,
                    self.media_stop_time,
                )

            if k == 'wifi':
                self.wifi_networks = network_data.process_wifi_networks(
                    v.file_path,
                    datetime_format=constants.DATETIME_UTC_FORMAT,
                    start_time=self.media_start_time,
                    end_time=self.media_stop_time,
                )

            if k == 'cell':
                self.cell_networks = network_data.process_cell_networks(
                    v.file_path,
                    datetime_format=constants.DATETIME_UTC_FORMAT,
                    start_time=self.media_start_time,
                    end_time=self.media_stop_time,
                )

            if k == 'label':
                self.label = csv_io.load_csv_data(
                    v.file_path, fieldnames=constants.LABELS_FILE_FIELDNAMES
                )

            if k == 'video' and extract_media:
                self.audio = media.extract_audio(v.file_path, v.file_path.replace('.mp4', '.wav'))
                self.gif = media.extract_gif(v.file_path, v.file_path.replace('.mp4', '.gif'))

        return True

    def extract_snippet(
        self, start_time, end_time, output_dir, include_time_span_on_filename=False
    ):
        """Export a UTC-aligned recording interval; negative end means its end."""
        start_time, end_time = snippets.normalize_snippet_time_bounds(start_time, end_time)
        origin, duration = metadata.recording_reference(self)
        start_time, end_time = snippets.resolve_snippet_time_bounds(start_time, end_time, duration)
        destination = Path(output_dir)

        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError('Snippet destination is not empty')

        destination.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix='.snippet-', dir=destination.parent) as temporary:
            staging = Path(temporary) / 'recording'
            staging.mkdir()

            if self.video is not None:
                filename = constants.VIDEO_FILE_NAME

                if include_time_span_on_filename:
                    filename = constants.VIDEO_SNIPPET_FILE_NAME.format(start_time, end_time)

                media.extract_video_snippet(self.video, start_time, end_time, staging / filename)
            else:
                extension = '.wav' if self.audio.lower().endswith('.wav') else '.m4a'
                filename = 'audio' + extension

                if include_time_span_on_filename:
                    filename = f'audio.{start_time}_{end_time}{extension}'

                media.extract_audio_snippet(self.audio, start_time, end_time, staging / filename)

            snippet_export.write_frame_snippets(
                self, start_time, end_time, staging, include_time_span_on_filename, origin
            )
            snippet_export.write_sensors_snippet(
                self, start_time, end_time, staging, include_time_span_on_filename, origin
            )
            snippet_export.write_metadata_snippet(
                self, start_time, end_time, staging, include_time_span_on_filename
            )

            if destination.exists():
                destination.rmdir()

            staging.rename(destination)

        return destination

    def split(self, segment_duration, output_dir):
        """Export consecutive fixed-duration segments, keeping the final remainder."""
        segment_duration = float(segment_duration)

        if not math.isfinite(segment_duration) or segment_duration <= 0:
            raise ValueError('Segment duration must be positive and finite')

        _, duration = metadata.recording_reference(self)
        destination = Path(output_dir)

        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError('Split destination is not empty')

        destination.parent.mkdir(parents=True, exist_ok=True)
        count = math.ceil(duration / segment_duration)

        with tempfile.TemporaryDirectory(prefix='.split-', dir=destination.parent) as temporary:
            staging = Path(temporary) / 'segments'
            staging.mkdir()

            for index in range(count):
                start = index * segment_duration
                end = min((index + 1) * segment_duration, duration)
                self.extract_snippet(start, end, staging / f'segment-{index + 1:04d}')

            if destination.exists():
                destination.rmdir()

            staging.rename(destination)

        return [destination / f'segment-{index + 1:04d}' for index in range(count)]

    def extract_frames(self, output_dir=None, step=None, prefix='', left_zeros=5):
        """Return regularly spaced frames, or saved paths when output_dir is supplied."""
        if self.video is None:
            raise ValueError('Frame extraction requires a video recording')

        return media.extract_frames(
            self.video,
            output_dir,
            step,
            prefix,
            left_zeros,
        )

    def extract_frames_at_times(self, times, output_dir=None, prefix='', left_zeros=5):
        """Return frames at requested seconds, or saved paths when output_dir is supplied."""
        if self.video is None:
            raise ValueError('Frame extraction requires a video recording')

        return media.extract_frames_at_times(
            self.video,
            times,
            output_dir,
            prefix,
            left_zeros,
        )

    def extract_frames_at_positions(self, positions, output_dir=None, prefix='', left_zeros=5):
        """Return frames at requested positions, in memory or as saved paths."""
        if self.video is None:
            raise ValueError('Frame extraction requires a video recording')

        return media.extract_frames_at_positions(
            self.video,
            positions,
            output_dir,
            prefix,
            left_zeros,
        )

    def extract_frames_timespan(
        self, start_time, end_time, output_dir=None, step=None, prefix='', left_zeros=5
    ):
        """Return frames within an interval in seconds, in memory or as saved paths."""
        if self.video is None:
            raise ValueError('Frame extraction requires a video recording')

        return media.extract_frames_timespan(
            self.video,
            start_time,
            end_time,
            output_dir,
            step,
            prefix,
            left_zeros,
        )

    def extract_frames_positionspan(
        self, start_position, end_position, output_dir=None, step=None, prefix='', left_zeros=5
    ):
        """Return frames within a position interval, in memory or as saved paths."""
        if self.video is None:
            raise ValueError('Frame extraction requires a video recording')

        return media.extract_frames_positionspan(
            self.video,
            start_position,
            end_position,
            output_dir,
            step,
            prefix,
            left_zeros,
        )

    def calculate_sample_distance_traveled(self):
        """Calculates the distance traveled within a single sample, in km."""
        df_gps = self.geolocation_points.copy() if self.geolocation_points is not None else None

        if df_gps is None or df_gps.empty or len(df_gps) < 2:
            return 0.0

        df_gps = df_gps.sort_values(by='Datetime UTC')
        df_gps['latitude'] = pd.to_numeric(df_gps['latitude'], errors='coerce')
        df_gps['longitude'] = pd.to_numeric(df_gps['longitude'], errors='coerce')
        df_gps = df_gps.dropna(subset=['latitude', 'longitude'])

        if len(df_gps) < 2:
            return 0.0

        df_gps['latitude_next'] = df_gps['latitude'].shift(-1)
        df_gps['longitude_next'] = df_gps['longitude'].shift(-1)
        mask = df_gps['latitude_next'].notnull() & df_gps['longitude_next'].notnull()

        distances = df_gps.loc[mask].apply(
            lambda row: geolocation.calculate_haversine_distance(
                row['latitude'], row['longitude'], row['latitude_next'], row['longitude_next']
            ),
            axis=1,
        )

        return float(distances.sum())
