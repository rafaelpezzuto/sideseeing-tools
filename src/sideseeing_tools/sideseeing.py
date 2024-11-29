import datetime
import json
import os
import random
import re

from sideseeing_tools import (
    constants, 
    exceptions,
    media,
    utils,
)


class SideSeeingDS:
    def __init__(
            self, 
            root_dir,
            subdir_data='.',
            name='MyDataset', 
            generate_metadata=False,
            extract_media=False,
        ):
        print('INFO. Loading data.')
        self.name = name
        
        if not os.path.isdir(root_dir):
            raise exceptions.RootDirIsNotADirectoryError()

        self.root_dir = root_dir if root_dir.endswith(os.path.sep) else f'{root_dir}{os.path.sep}'
        self.data_dir = os.path.join(self.root_dir, subdir_data)
        self.setup(extract_media)

        if generate_metadata:
            self.metadata(generate_metadata)
        print('INFO. Done.')

    def setup(self, extract_media):
        self.instances = {}
        for root, _, files in os.walk(self.data_dir):
            for f in files:
                if f not in constants.SUPPORTED_FILES:
                    print(f'WARNING. {os.path.join(root, f)} has been ignored.')
                    continue

                ssf = SideSeeingFile(self.data_dir, os.path.join(root, f))
                if ssf.is_valid:
                    if ssf.name not in self.instances:
                        self.instances[ssf.name] = SideSeeingInstance(
                                ssf.name,
                                ssf.path,
                            )
                    self.instances[ssf.name].add_file(ssf)

        for key in self.instances.keys():
            self.instances[key].setup(extract_media)

        self.populate_sensors()

    def populate_sensors(self):
        self.sensors = {
            'sensors1': {},
            'sensors3': {},
            'sensors6': {},
        }

        for instance in self.iterator:
            for n_axis in self.sensors.keys():
                if hasattr(instance, n_axis):
                    for name in getattr(instance, n_axis).keys():
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

    def metadata(self, save=False):
        if self.size == 0:
            print(f'ERROR. Dataset is empty.')
            return

        path = os.path.join(f'{self.root_dir}', 'metadata.csv')

        if os.path.exists(path) and not save:
            df = utils.load_csv_data_with_pandas(path)

        if not os.path.exists(path) or save:
            df = utils.generate_metadata(self.iterator, constants.DATETIME_UTC_FORMAT)
            utils.save_csv_data_with_pandas(df, path)

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
        self.file_type = self.discover_file_type()
        self.path = os.path.dirname(self.file_path)
        self.name = self.gen_instance_name(self.file_path, self.data_dir)
        self.is_valid = False if self.file_type == 'unknown' else True

    def gen_instance_name(self, file_path, data_dir):
        els = f'{os.path.dirname(file_path)}'.replace(data_dir, '').split(os.path.sep)
        return '#'.join(els[1:])

    def discover_file_type(self):
        if self.file_name.endswith('metadata.json'):
            return 'metadata'
        elif (self.file_name.endswith('labels.txt') or self.file_name.endswith('labels.csv')):
            return 'label'
        elif re.search(r'consumption(\.\d+_\d+)?\.csv$', self.file_name):
            return 'consumption'
        elif re.search(r'gps(\.\d+_\d+)?\.csv$', self.file_name):
            return 'gps'
        elif re.search(r'sensors\.three(\.\d+_\d+)?\.csv$', self.file_name):
            return 'sensors3'
        elif re.search(r'sensors\.three\.uncalibrated(\.\d+_\d+)?\.csv$', self.file_name):
            return 'sensors6'
        elif re.search(r'sensors\.one(\.\d+_\d+)?\.csv$', self.file_name):
            return 'sensors1'
        elif self.file_name.endswith('.mp4'):
            return 'video'
        elif self.file_name.endswith('video.wav'):
            return 'audio'
        elif self.file_name.endswith('video.gif'):
            return 'gif'
        else:
            print(f'WARNING. Unknown file type detected: {self.file_path}.')
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

    def add_file(self, ssf: SideSeeingFile):
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
            f"Start video time: {self.metadata.get('time', {}).get('videoStartDateTime', '')}",
            f"Stop video time: {self.metadata.get('time', {}).get('videoStopDateTime', '')}",
            sep='\n'
        )

    def setup(self, extract_media=False):
        try:
            with open(self.files['metadata'].file_path) as json_file:
                self.metadata = json.load(json_file)
        except KeyError:
            raise exceptions.MetadataFileDoesNotExistError(f'ERROR. Metadata file is missing for {self.name}')

        if self.metadata is None:
            raise exceptions.InvalidMetadataFileError(f'ERROR. Metadata file is is invalid for {self.name}')

        self.video_start_time = datetime.datetime.strptime(self.metadata['time']['videoStartDateTime'], constants.DATETIME_UTC_FORMAT)
        self.video_stop_time = datetime.datetime.strptime(self.metadata['time']['videoStopDateTime'], constants.DATETIME_UTC_FORMAT)
        self.video_total_time = (self.video_stop_time - self.video_stop_time).total_seconds()

        for k, v in self.files.items():
            if k == 'consumption':
                self.consumption = utils.preprocess_consumption(
                    utils.load_csv_data(v.file_path, fieldnames=constants.CONSUMPTION_FILE_FIELDNAMES),
                    constants.DATETIME_UTC_FORMAT,
                    self.video_start_time,
                    self.video_stop_time,
                )

            if k == 'gps':
                self.geolocation_points = utils.preprocess_gps(
                    utils.load_csv_data(v.file_path, fieldnames=constants.GPS_FILE_FIELDNAMES),
                    constants.DATETIME_UTC_FORMAT,
                    self.video_start_time,
                    self.video_stop_time,
                )
                if not self.geolocation_points.empty:
                    self.geolocation_center = self.geolocation_points[['latitude', 'longitude']].mean().tolist()
                else:
                    self.geolocation_center = None

            if k == 'sensors3':
                self.sensors3 = utils.preprocess_sensors(
                    utils.load_csv_data(v.file_path, fieldnames=constants.THREE_AXES_SENSORS_FILE_FIELDNAMES),
                    3,
                    constants.DATETIME_UTC_FORMAT,
                    self.video_start_time,
                    self.video_stop_time
                )

            if k == 'sensors6':
                self.sensors6 = utils.preprocess_sensors(
                    utils.load_csv_data(v.file_path, fieldnames=constants.THREE_AXES_UNCALIBRATED_SENSORS_FILE_FIELDNAMES),
                    6,
                    constants.DATETIME_UTC_FORMAT,
                    self.video_start_time,
                    self.video_stop_time
                )

            if k == 'sensors1':
                self.sensors1 = utils.preprocess_sensors(
                    utils.load_csv_data(v.file_path, fieldnames=constants.ONE_AXIS_SENSORS_FILE_FIELDNAMES),
                    1,
                    constants.DATETIME_UTC_FORMAT,
                    self.video_start_time,
                    self.video_stop_time
                )

            if k == 'label':
                self.label = utils.load_csv_data(v.file_path, fieldnames=constants.LABELS_FILE_FIELDNAMES)

            if k == 'video':
                self.video = v.file_path
                if extract_media:
                    self.audio = media.extract_audio(v.file_path, v.file_path.replace('.mp4', '.wav'))
                    self.gif = media.extract_gif(v.file_path, v.file_path.replace('.mp4', '.gif'))

    def extract_snippet(self, start_time, end_time, output_dir):
        '''
        Extract a snippet from the instance.

        Args:
            start_time (int): The start time in seconds.
            end_time (int): The end time in seconds.
            output_dir (str): The output directory where the snippet will be saved.
        
        Returns:
            None
        '''
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        self._write_gps_snippet(start_time, end_time, output_dir)

        self._write_consumption_snippet(start_time, end_time, output_dir)
            
        self._write_sensors_snippet(start_time, end_time, output_dir)

        media.extract_video_snippet(
            self.video, 
            start_time, 
            end_time, 
            os.path.join(output_dir, constants.VIDEO_SNIPPET_FILE_NAME.format(start_time, end_time)),
        )

    def _write_sensors_snippet(self, start_time, end_time, output_dir):
        sensor_configs = [
            ('sensors1', constants.ONE_AXIS_SNIPPET_FILE_NAME, constants.ONE_AXIS_SENSORS_FILE_FIELDNAMES),
            ('sensors3', constants.THREE_AXES_SNIPPET_FILE_NAME, constants.THREE_AXES_SENSORS_FILE_FIELDNAMES),
            ('sensors6', constants.THREE_AXES_UNCALIBRATED_SNIPPET_FILE_NAME, constants.THREE_AXES_UNCALIBRATED_SENSORS_FILE_FIELDNAMES),
        ]

        for naxes, file_name, fields in sensor_configs:
            output_file = os.path.join(output_dir, file_name.format(start_time, end_time))
            sensors = getattr(self, naxes, {})

            with open(output_file, 'w') as fout:
                fout.write(','.join(fields) + '\n')
                
                for sensor_name, sensor_data in sensors.items():
                    sensor_snippet_data = utils.extract_dataframe_snippet(sensor_data, start_time, end_time)
                    axis_data = []
                    for col in fields:
                        if col in ['axis_x', 'axis_y', 'axis_z']:
                            axis_data.append(col.replace('axis_', ''))
                        elif col in ['delta_x', 'delta_y', 'delta_z']:
                            axis_data.append(col.replace('delta_', ''))

                    for _, row in sensor_snippet_data.iterrows():
                        formatted_row = [
                            row['timestamp_nano'],
                            row['Datetime UTC'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                            sensor_name,
                        ] + [row[a] for a in axis_data] + [row['accuracy']]
        
                        fout.write(','.join(map(str, formatted_row)) + '\n')

    def _write_consumption_snippet(self, start_time, end_time, output_dir):
        consumption_snippet_output_file = os.path.join(output_dir, constants.CONSUMPTION_SNIPPET_FILE_NAME.format(start_time, end_time))
        consumption_snippet_data = utils.extract_dataframe_snippet(self.consumption, start_time, end_time)
        with open(consumption_snippet_output_file, 'w') as fout:
            fout.write(','.join(constants.CONSUMPTION_FILE_FIELDNAMES) + '\n')
            for _, row in consumption_snippet_data.iterrows():
                formatted_row = [
                    row['Datetime UTC'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                    row['battery_microamperes']
                ]
                fout.write(','.join(map(str, formatted_row)) + '\n')

    def _write_gps_snippet(self, start_time, end_time, output_dir):
        gps_snippet_output_file = os.path.join(output_dir, constants.GPS_SNIPPET_FILE_NAME.format(start_time, end_time))
        gps_snippet_data = utils.extract_dataframe_snippet(self.geolocation_points, start_time, end_time)
        with open(gps_snippet_output_file, 'w') as fout:
            fout.write(','.join(constants.GPS_FILE_FIELDNAMES) + '\n')
            for _, row in gps_snippet_data.iterrows():
                formatted_row = [
                    row['Datetime UTC'].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                    row['gps_interval'],
                    row['accuracy'],
                    row['latitude'],
                    row['longitude']
                ]
                fout.write(','.join(map(str, formatted_row)) + '\n')

    def extract_frames(self, output_dir, step=None, prefix='', left_zeros='5'):
        '''
        Extract frames from the video.

        Args:
            output_dir (str): The output directory where the frames will be saved.
            step (int): The rate at which frames are extracted.
            prefix (str): A prefix for the frame file names.
            left_zeros (str): The number of left zeros for the frame file names.
        
        Returns:
            list: A list of the extracted frames file paths.
        '''
        return media.extract_frames(
            self.video, 
            output_dir,
            step,
            prefix,
            left_zeros,
        )

    def extract_frames_at_times(self, output_dir, times, prefix='', left_zeros='5'):
        '''
        Extract frames at specific times from the video.

        Args:
            output_dir (str): The output directory where the frames will be saved.
            times (list): A list of times in seconds.
            prefix (str): A prefix for the frame file names.
            left_zeros (str): The number of left zeros for the frame file names.

        Returns:
            list: A list of the extracted frames file paths.
        '''
        return media.extract_frames_at_times(
            self.video,
            output_dir,
            times,
            prefix,
            left_zeros,
        )
    
    def extract_frames_at_positions(self, output_dir, positions, prefix='', left_zeros='5'):
        '''
        Extract frames at specific positions from the video.

        Args:
            output_dir (str): The output directory where the frames will be saved.
            positions (list): A list of frame positions.
            prefix (str): A prefix for the frame file names.
            left_zeros (str): The number of left zeros for the frame file names.

        Returns:
            list: A list of the extracted frames file paths.
        '''
        return media.extract_frames_at_positions(
            self.video,
            output_dir,
            positions,
            prefix,
            left_zeros,
        )
    
    def extract_frames_timespan(self, output_dir, start_time, end_time, step=None, prefix='', left_zeros='5'):
        '''
        Extract frames from a timespan of the video.

        Args:
            output_dir (str): The output directory where the frames will be saved.
            start_time (int): The start time in seconds.
            end_time (int): The end time in seconds.
            step (int): The rate at which frames are extracted.
            prefix (str): A prefix for the frame file names.
            left_zeros (str): The number of left zeros for the frame file names.

        Returns:
            list: A list of the extracted frames file paths.
        '''
        return media.extract_frames_timespan(
            self.video,
            output_dir,
            start_time,
            end_time,
            step,
            prefix,
            left_zeros,
        )

    def extract_frames_positionspan(self, output_dir, start_position, end_position, step=None, prefix='', left_zeros='5'):
        '''
        Extract frames from a position span of the video.

        Args:
            output_dir (str): The output directory where the frames will be saved.
            start_position (int): The start position in frames.
            end_position (int): The end position in frames.
            step (int): The rate at which frames are extracted.
            prefix: (str): A prefix for the frame file names.
            left_zeros (str): The number of left zeros for the frame file names.

        Returns:
            list: A list of the extracted frames file paths.
        '''
        return media.extract_frames_positionspan(
            self.video,
            output_dir,
            start_position,
            end_position,
            step,
            prefix,
            left_zeros,
        )
