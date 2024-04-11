import datetime
import json
import os

import cv2
import folium
import librosa
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
            generate_metadata=True,
            extract_media=True,
        ):
        self.name = name
        
        if not os.path.isdir(root_dir):
            raise exceptions.RootDirIsNotADirectoryError()

        if not os.path.exists(root_dir):
            raise exceptions.RootDirDoesNotExistError()

        self.root_dir = root_dir if root_dir.endswith(os.path.sep) else f'{root_dir}{os.path.sep}'
        self.data_dir = os.path.join(self.root_dir, subdir_data)
        self.setup(extract_media)

        if generate_metadata:
            self.metadata(generate_metadata)

    def setup(self, extract_media):
        self.instances = {}
        for root, _, files in os.walk(self.data_dir):
            for f in files:
                if 'generated' in os.path.join(root, f) or f not in constants.SUPPORTED_FILES:
                    print(f'WARNING. {os.path.join(root, f)} has been ignored.')
                    continue

                ssf = SideSeeingFile(self.data_dir, os.path.join(root, f))
                if ssf.is_valid:
                    if ssf.instance_name not in self.instances:
                        self.instances[ssf.instance_name] = SideSeeingInstance(
                                ssf.instance_name,
                                ssf.instance_path,
                            )
                    self.instances[ssf.instance_name].add_file(ssf)

        for key in self.instances.keys():
            self.instances[key].setup(extract_media)

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
            df = pd.read_csv(path)

        if not os.path.exists(path) or save:
            df = pd.DataFrame()

            items = []
            for i in self.iterator:
                cap = cv2.VideoCapture(i.video)
                v_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                v_fps = cap.get(cv2.CAP_PROP_FPS)
                v_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                v_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()

                item = {}

                item['name'] = i.instance_name
                item['video_start_time'] = datetime.datetime.strptime(i.metadata.get('time', {}).get('videoStartDateTime', ''), constants.DATETIME_UTC_FORMAT)
                item['video_end_time'] = datetime.datetime.strptime(i.metadata.get('time', {}).get('videoStopDateTime', ''), constants.DATETIME_UTC_FORMAT)
                item['video_duration'] = round(v_frames / v_fps, 2)
                item['video_frames'] = v_frames
                item['video_fps'] = v_fps
                item['video_resolution'] = f'{v_width}x{v_height}'
                item['manufacturer'] = i.metadata.get('device', {}).get('manufacturer', '')
                item['model'] = i.metadata.get('device', {}).get('model', '')
                item['so_version'] = i.metadata.get('device', {}).get('androidVersion', '')

                items.append(item)

            df = pd.DataFrame.from_dict(items)
            df.to_csv(path, index=False)

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
        self.instance_path = os.path.dirname(self.file_path)
        self.instance_name = self.gen_instance_name(self.file_path, self.data_dir)
        self.is_valid = False if self.file_type == 'unknown' else True

    def gen_instance_name(self, file_path, data_dir):
        els = f'{os.path.dirname(file_path)}'.replace(data_dir, '').split(os.path.sep)
        return '#'.join(els[1:])

    def discover_file_type(self):
        if self.file_name.endswith('metadata.json'):
            return 'metadata'
        elif (self.file_name.endswith('labels.txt') or self.file_name.endswith('labels.csv')):
            return 'label'
        elif self.file_name.endswith('consumption.csv'):
            return 'consumption'
        elif self.file_name.endswith('gps.csv'):
            return 'gps'
        elif self.file_name.endswith('sensors.three.csv'):
            return 'sensors3'
        elif self.file_name.endswith('sensors.three.uncalibrated.csv'):
            return 'sensors6'
        elif self.file_name.endswith('sensors.one.csv'):
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
    def __init__(self, instance_name, instance_path):
        self.instance_name = instance_name
        self.instance_path = instance_path
        self.files = {}

    def add_file(self, ssf: SideSeeingFile):
        self.files[ssf.file_type] = ssf

    def __str__(self):
        return f'SSInstance[instance_name: {self.instance_name}]'

    def __repr__(self):
        return self.__str__()

    def print_metadata(self):
        print(f"----\nName: {self.instance_name}")
        print(
            f"Path: {self.instance_path}",
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
            raise exceptions.MetadataFileDoesNotExistError(f'ERROR. Metadata file is missing for {self.instance_name}')

        if self.metadata is None:
            raise exceptions.InvalidMetadataFileError(f'ERROR. Metadata file is is invalid for {self.instance_name}')

        self.video_start_time = datetime.datetime.strptime(self.metadata['time']['videoStartDateTime'], constants.DATETIME_UTC_FORMAT)
        self.video_stop_time = datetime.datetime.strptime(self.metadata['time']['videoStopDateTime'], constants.DATETIME_UTC_FORMAT)

        for k, v in self.files.items():
            if k == 'consumption':
                self.consumption = utils.load_csv_data(v.file_path, fieldnames=constants.CONSUMPTION_FILE_FIELDNAMES)

            if k == 'gps':
                self.geolocation_points = np.array([[float(d['latitude']), float(d['longitude'])] for d in utils.load_csv_data(v.file_path, fieldnames=constants.GPS_FILE_FIELDNAMES)])
                self.geolocation_center = self.geolocation_points.mean(axis=0)

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


class SideSeeingPlotter:
    def __init__(self, dataset: SideSeeingDS, path_taxonomy: str=None, google_api_key: str=None):
        self.dataset = dataset
        if path_taxonomy:
            self.categories_and_tags = utils.load_csv_data(path_taxonomy, fieldnames=constants.LABELS_FILE_FIELDNAMES)
        else:
            self.categories_and_tags = []
        self.google_api_key = google_api_key

    def plot_instance_audio(self, instance: SideSeeingInstance):
        '''
        Plots the waveform and the Mel spectrogram for the specified audio file.
        '''
        y, sr = librosa.load(instance.audio)
        M = librosa.feature.melspectrogram(y=y, sr=sr)
        M_db = librosa.power_to_db(M, ref=np.max)

        fig, ax = plt.subplots(nrows=2, sharex=True)
        librosa.display.waveshow(y, sr=sr, ax=ax[0])
        ax[0].set(title='Waveform')
        ax[0].label_outer()

        img1 = librosa.display.specshow(M_db, y_axis='mel', x_axis='time', ax=ax[1])
        ax[1].set(title='Mel spectrogram')
        fig.colorbar(img1, ax=ax[1], format="%+2.f dB", location='bottom')

    def plot_instance_map(self, instance: SideSeeingInstance, titles='OpenStreetMap', zoom_start=14):
        if instance is None or not isinstance(instance, SideSeeingInstance):
            print(f'ERROR. You have to pass an instance (SideSeeingInstance).')
            return
        
        points = instance.geolocation_points
        center = instance.geolocation_center

        if len(points) > 0:
            map = folium.Map(location=center, titles=titles, zoom_start=zoom_start)
            counter = 1

            for lat, lon in points:
                if counter == 1:
                    color = 'red'
                elif counter == len(points):
                    color = 'green'
                else:
                    color = 'blue'

                folium.Marker([lat, lon], icon=folium.Icon(color=color)).add_to(map)
                counter += 1

            folium.LayerControl().add_to(map)
            display(map)
        else:
            print('WARNING. GPS data is missing.')

    def plot_instance_video_frames(self, instance: SideSeeingInstance):
        '''
        Plots a sample of frames for the specified video.
        '''
        cap = cv2.VideoCapture(instance.video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_indices = [0] + [int(i * total_frames / 10) for i in range(1, 10)]

        rows = 2
        cols = 5
        fig, axes = plt.subplots(rows, cols, figsize=(15, 6))

        for i, idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            time_in_seconds = idx / fps

            ax = axes[i // cols, i % cols]
            ax.imshow(frame_rgb)
            ax.set_title(f'Frame {idx} - {time_in_seconds:.1f} s')

            ax.set_xticks([])
            ax.set_yticks([])

        plt.tight_layout()
        plt.show()
        cap.release()

    def plot_instance_video_frames_at_times(self, instance: SideSeeingInstance, times: list):
        '''
        Plots frames for the specified video at the given time points.
        '''
        cap = cv2.VideoCapture(instance.video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        num_frames = len(times)

        max_cols = 5

        if num_frames <= max_cols:
            rows = 1
            cols = num_frames
            figsize = (15, 3)
        else:
            rows = int(num_frames / max_cols) + 1
            cols = 5
            figsize = (15, 2 * rows)

        fig, axes = plt.subplots(rows, cols, figsize=figsize)

        rc = 0
        cc = 0
        for i, time_in_seconds in enumerate(times):
            frame_idx = int(time_in_seconds * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

            ret, frame = cap.read()

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if rows > 1:
                ax = axes[rc][cc]
            else:
                ax = axes[cc]

            ax.imshow(frame_rgb)
            ax.set_title(f'{time_in_seconds:.1f} s' )

            ax.set_xticks([])
            ax.set_yticks([])

            if cc < max_cols - 1:
                cc += 1
            else:
                cc = 0
                rc += 1

        [fig.delaxes(ax) for ax in axes.flatten() if not ax.has_data()]
        plt.tight_layout()
        plt.show()
        cap.release()

    def plot_instance_sensors3_and_audio(self, instance: SideSeeingInstance, main_title='', x_ti=0, x_tf=None):
        '''
        Creates a plot for the sensors and audio data.
        It is useful for plotting data related with an instance/sample.
        '''
        num_sensor_subplots = len(instance.sensors3.keys())
        num_audio_subplots = 2
        total_subplots = num_sensor_subplots + num_audio_subplots

        fig, axis = plt.subplots(total_subplots, 2, figsize=(15, 15), width_ratios=[3, 1], sharex=False)
        fig.suptitle(main_title, fontsize=15)

        for ind, sensor_name in enumerate(sorted(instance.sensors3.keys())):
            sensor_data = instance.sensors3[sensor_name]

            if not x_tf:
                x_tf = sensor_data['Time (s)'].iloc[-1]

            axis[ind, 0].set_ylabel(sensor_name)

            axis[ind, 0].plot(sensor_data['Time (s)'], sensor_data['x'], label='x', linewidth=0.75)
            axis[ind, 0].plot(sensor_data['Time (s)'], sensor_data['y'], label='y', linewidth=0.75)
            axis[ind, 0].plot(sensor_data['Time (s)'], sensor_data['z'], label='z', linewidth=0.75)
            axis[ind, 0].set_xlabel('Time (s)')
            axis[ind, 0].set_xlim((x_ti, x_tf))

            axis[ind, 1].hist(sensor_data['x'], label='x', alpha=0.4)
            axis[ind, 1].hist(sensor_data['y'], label='y', alpha=0.4)
            axis[ind, 1].hist(sensor_data['z'], label='z', alpha=0.4)
            axis[ind, 1].set_ylabel('Frequency')

            axis[ind, 0].legend()
            axis[ind, 1].legend()

            if ind == num_sensor_subplots - 1:
                y, sr = librosa.load(instance.audio)
                M = librosa.feature.melspectrogram(y=y, sr=sr)
                M_db = librosa.power_to_db(M, ref=np.max)

                librosa.display.waveshow(y, sr=sr, ax=axis[ind + 1, 0])
                axis[ind + 1, 0].set_xlim((x_ti, x_tf))
                axis[ind + 1, 0].set_ylabel('Waveform')
                axis[ind + 1, 0].set_xlabel('Time (s)')

                img = librosa.display.specshow(
                        M_db,
                        y_axis='mel',
                        x_axis='time',
                        ax=axis[ind + 2, 0]
                )
                axis[ind + 2, 0].set_xlim((x_ti, x_tf))
                axis[ind + 2, 0].set_ylabel('Mel spectrogram (Hz)')
                axis[ind + 2, 0].set_xlabel('Time (s)')

                fig.colorbar(
                        img,
                        ax=axis[ind + 2, 1],
                        format="%+2.f dB",
                        location='left'
                )

                axis[ind + 1, 1].axis('off')
                axis[ind + 2, 1].axis('off')

        plt.tight_layout()
        plt.show()

    def plot_dataset_tags(self):
        if len(self.categories_and_tags) == 0:
            print('WARNING. There are no categories and tags loaded. Check the taxonomy file.')
            return

        labels = {}
        for l in self.categories_and_tags:
            cat, tag = l['category'], l['tag']
            k = f'{cat},{tag}'.replace(' ', '_')
            labels[k] = 0

        for instance in self.dataset.iterator:
            if not hasattr(instance, 'label'):
                print(f"WARNING. {instance.instance_name} isn't labeled.")
            else:
                for l in instance.label:
                    cat, tag = l['category'], l['tag']
                    k = f'{cat},{tag}'.replace(' ', '_')
                    if k not in labels:
                        labels[k] = 0
                    labels[k] += 1

        df = pd.DataFrame.from_dict(data=labels, orient='index', columns=['Frequency'])
        df = df.fillna(0)
        df = df.astype(int)
        df = df.sort_values('Frequency', ascending=False)

        return df.style.applymap(func=lambda x: 'color: red' if x < 1 else 'color: black')
    
    def plot_dataset_tags_matrix(self, primary_category, secondary_category):
        if len(self.categories_and_tags) == 0:
            print('WARNING. There are no categories and tags loaded. Check the taxonomy file.')
            return
        
        if primary_category is None or secondary_category is None:
            print(f'ERROR. You must pass a category name.')
            print(f'Here are the possibilities: {self.categories_and_tags.keys()}.')
            return

        matrix = {}

        for ct in self.categories_and_tags:
            c = ct['category']
            t = ct['tag']

            if c == primary_category:
                matrix[t] = {}

        for st in matrix:
            for ct in self.categories_and_tags:
                c = ct['category']
                t = ct['tag']

                if c == secondary_category:
                    matrix[st][t] = 0

        for instance in self.dataset.iterator:
            if not hasattr(instance, 'label'):
                print(f"WARNING. {instance.instance_name} isn't labeled.")
            else:
                instance_st = set()
                for l in instance.label:
                    cat, tag = l['category'], l['tag']
                    if cat == primary_category:
                        instance_st.add(tag)

                for l in instance.label:
                    cat, tag = l['category'], l['tag']
                    if cat == secondary_category:
                        for s in instance_st:
                            matrix[s][tag] += 1

        df = pd.DataFrame(data=matrix)
        df = df.fillna(0)
        df = df.astype(int)

        return df.style.applymap(func=lambda x: 'color: red' if x < 1 else 'color: black')
    
    def plot_dataset_sensors3(self, sensor_name: str, initial_xlim=(0, 30), identifiers=[]):
        '''
        Creates a subplot composed of 1xn time series where n is the number of instances/samples. It is required to indicate the sensor's name.
        '''
        _content = []

        if len(identifiers) == 0:
            for i in self.dataset.iterator:
                _content.append([
                        i.instance_name,
                        i.sensors3.get(sensor_name, [])
                ])
        else:
            for i in identifiers:
                _instance = self.dataset.instances.get(i, None)
                if not _instance:
                    print(f'WARNING. {i} does not exist.')
                    continue

                _content.append([
                        _instance.instance_name,
                        _instance.sensors3.get(sensor_name, [])
                ])

        _, axis = plt.subplots(len(_content), 1, figsize=(15, int(len(_content) * 4)), sharex=True)

        for ind, _key_sensor in enumerate(_content):
            _key, _sensor_data = _key_sensor

            axis[ind].plot(_sensor_data['Time (s)'], _sensor_data['x'], label='x', linewidth=0.75)
            axis[ind].plot(_sensor_data['Time (s)'], _sensor_data['y'], label='y', linewidth=0.75)
            axis[ind].plot(_sensor_data['Time (s)'], _sensor_data['z'], label='z', linewidth=0.75)
            axis[ind].set_title(_key)
            axis[ind].legend()
            axis[ind].set_xlim(initial_xlim)

        plt.tight_layout()
        plt.show()

    def plot_dataset_map(self, titles='OpenStreetMap', zoom_start=4):
        points = np.vstack([i.geolocation_points for i in self.dataset.iterator])
        center = points.mean(axis=0)

        ds_map = folium.Map(location=center, titles=titles, zoom_start=zoom_start)

        for lat, lon in points:
            folium.Marker([lat, lon]).add_to(ds_map)

        folium.LayerControl().add_to(ds_map)
        display(ds_map)

    def plot_dataset_cities(self):
        points = np.vstack([i.geolocation_center for i in self.dataset.iterator])

        geo = {}
        for lat, long in points:
            location = utils.inverse_geocode(lat, long, self.google_api_key)
            key = f"{location['country']},{location['city']}"

            if key not in geo:
                geo[key] = {'Frequency': 0}

            geo[key]['Frequency'] += 1

        df = pd.DataFrame.from_dict(data=geo, orient='index', columns=['Frequency'])
        df = df.fillna(0)
        df = df.sort_values('Frequency', ascending=False)

        return df.style.applymap(func=lambda x: 'color: red' if x < 1 else 'color: black')
