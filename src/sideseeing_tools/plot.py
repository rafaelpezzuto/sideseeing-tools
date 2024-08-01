import cv2
import folium
import librosa
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matplotlib import animation

from sideseeing_tools import constants, media, utils
from sideseeing_tools import sideseeing as sst


class SideSeeingPlotter:
    def __init__(self, dataset: sst.SideSeeingDS, path_taxonomy: str=None, google_api_key: str=None):
        self.dataset = dataset
        if path_taxonomy:
            self.categories_and_tags = utils.load_csv_data(path_taxonomy, fieldnames=constants.LABELS_FILE_FIELDNAMES)
        else:
            self.categories_and_tags = []
        self.google_api_key = google_api_key

    def plot_instance_audio(self, instance: sst.SideSeeingInstance):
        '''
        Plots the waveform and the Mel spectrogram for the specified audio file.
        '''
        if not hasattr(instance, 'audio'):
            print(f'Extracting audio data')
            instance.audio = media.extract_audio(
                instance.video, 
                instance.video.replace('.mp4', '.wav')
            )

        y, sr = librosa.load(instance.audio)
        M = librosa.feature.melspectrogram(y=y, sr=sr)
        M_db = librosa.power_to_db(M, ref=np.max)

        fig, ax = plt.subplots(nrows=2, sharex=True)
        librosa.display.waveshow(y, sr=sr, ax=ax[0], color="blue")
        ax[0].set(title='Waveform')
        ax[0].label_outer()

        img1 = librosa.display.specshow(M_db, y_axis='mel', x_axis='time', ax=ax[1])
        ax[1].set(title='Mel spectrogram')
        fig.colorbar(img1, ax=ax[1], format="%+2.f dB", location='bottom')
        plt.tight_layout()
        plt.show()

    def plot_instance_map(self, instance: sst.SideSeeingInstance, titles='OpenStreetMap', zoom_start=14):        
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
            return map
        else:
            print('WARNING. GPS data is missing.')

    def plot_instance_video_frames(self, instance: sst.SideSeeingInstance):
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

    def plot_instance_video_frames_at_times(self, instance: sst.SideSeeingInstance, times: list, show_frame_number=True):
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
            if show_frame_number:
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

    def plot_instance_sensors3_and_audio(self, instance: sst.SideSeeingInstance, main_title='', x_ti=0, x_tf=None):
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
                if not hasattr(instance, 'audio'):
                    print(f'Extracting audio data')
                    instance.audio = media.extract_audio(
                        instance.video, 
                        instance.video.replace('.mp4', '.wav')
                    )

                y, sr = librosa.load(instance.audio)
                M = librosa.feature.melspectrogram(y=y, sr=sr)
                M_db = librosa.power_to_db(M, ref=np.max)

                librosa.display.waveshow(y, sr=sr, ax=axis[ind + 1, 0], color="blue")
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
                print(f"WARNING. {instance.name} isn't labeled.")
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
                print(f"WARNING. {instance.name} isn't labeled.")
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
    
    def plot_dataset_map(self, titles='OpenStreetMap', zoom_start=4):
        points = np.vstack([i.geolocation_points for i in self.dataset.iterator])
        center = points.mean(axis=0)

        ds_map = folium.Map(location=center, titles=titles, zoom_start=zoom_start)

        for lat, lon in points:
            folium.Marker([lat, lon]).add_to(ds_map)

        folium.LayerControl().add_to(ds_map)
        return ds_map

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

    def generate_video_sensor3(self, instance: sst.SideSeeingInstance, sensor_name: str, output_path: str, use_dynamic_xaxis=True, dpi=90, figsize = (25, 4), linewidth=5):
        plt.ion()

        mpl.rcParams['lines.linewidth'] = linewidth
        mpl.rcParams['font.family'] = "monospace"

        fig, ax = plt.subplots(1, 1, figsize = figsize)

        try:
            data = instance.sensors3[sensor_name]
        except KeyError:
            print(f'ERROR. {sensor_name}\'s data does not exist.')
            return

        time_min = np.min(data['Time (s)'])
        time_max = np.max(data['Time (s)'])
        axis_min = np.min(np.min(data[['x', 'y', 'z']]))
        axis_max = np.max(np.max(data[['x', 'y', 'z']]))
        axis_dt = int(abs((axis_max - axis_min)) * 0.1) or 1

        fps = int(len(data['x'])/time_max)

        def animate(i):
            ax.cla()

            ax.xaxis.set_visible(False)
            ax.yaxis.set_visible(False)
            ax.set_facecolor((0, 0, 0, 1))
            ax.set_frame_on(False)
            fig.patch.set_alpha(1)

            if use_dynamic_xaxis:
                x_start = max(0, i - 100)
                x_end = i
                ax.set_xlim([data['Time (s)'][x_start], data['Time (s)'][x_end]])
            else:
                ax.set_xlim([time_min, time_max])

            ax.set_xlim()
            ax.set_ylim([axis_min - axis_dt, axis_max + axis_dt])

            ax.plot(data['Time (s)'][:i], data['x'][:i])
            ax.plot(data['Time (s)'][:i], data['y'][:i])
            ax.plot(data['Time (s)'][:i], data['z'][:i])

        anim = animation.FuncAnimation(fig, animate, frames=len(data['x']), interval=200, blit=False, repeat=False)
        plt.subplots_adjust(left=0.01, right=1, top=1, bottom=0.01)
        anim.save(
            output_path,
            codec='libx264rgb',
            dpi=dpi,
            fps=fps,
            writer='ffmpeg',
            savefig_kwargs={
            "transparent": True,
            "facecolor": "Black"
            }
        )

    def plot_dataset_frames_at_times(self, times, show_instance_name=True, show_frame_number=True):
        for instance in self.dataset.iterator:
            if show_instance_name:
                print(instance.name)
            self.plot_instance_video_frames_at_times(instance, times=times, show_frame_number=show_frame_number)

    def plot_sensor(self, data, time_column, axis_columns, xlim=None, ylim=None, title=None, linewidth=0.75, figsize=(20, 4)):
        fig, ax = plt.subplots(nrows=1, figsize=figsize)

        for ind, a in enumerate(axis_columns):
            ax.plot(data[time_column], data[a], label=axis_columns[ind], linewidth=linewidth)

        ax.set_title(title)

        if xlim:
            ax.set_xlim(xlim)

        if ylim:
            ax.set_ylim(ylim)

        ax.legend()
        fig.show()

    def plot_sensors(self, data, time_column, axis_columns, xlim=None, ylim=None, linewidth=0.75, sharex=True, sharey=True):
        if len(data) == 0:
            return

        _, axis = plt.subplots(len(data), 1, figsize=(15, int(len(data) * 4)), sharex=sharex, sharey=sharey)

        for ind_plot, item in enumerate(data):
            instance_name = item['instance_name']
            sensor_data = item['sensor_data']

            for ind, column in enumerate(axis_columns):
                axis[ind_plot].plot(sensor_data[time_column], sensor_data[column], label=axis_columns[ind], linewidth=linewidth)
                axis[ind_plot].set_title(instance_name)
                axis[ind_plot].legend()
    
            if xlim:
                axis[ind_plot].set_xlim(xlim)
            if ylim:
                axis[ind_plot].set_ylim(ylim)

        plt.tight_layout()
        plt.show()
