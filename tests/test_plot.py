import io
import os
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib.pyplot as plt
import pandas as pd

from sideseeing_tools import geolocation, media
from sideseeing_tools.plot import SideSeeingPlotter
from sideseeing_tools.sideseeing import SideSeeingDS


class TestSideSeeingPlotter(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/'))
        self.dataset = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")
        self.taxonomy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/taxonomy.csv'))

    def tearDown(self):
        plt.close('all')

    def test_plot_dataset_tags_handles_none_label(self):
        plotter = SideSeeingPlotter(self.dataset, path_taxonomy=self.taxonomy_path)
        instance = self.dataset.instances['instance-001']
        instance.label = None

        result = plotter.plot_dataset_tags()

        self.assertTrue((result.data['Frequency'] == 0).all())

    def test_plot_dataset_tags_matrix_handles_none_label(self):
        plotter = SideSeeingPlotter(self.dataset, path_taxonomy=self.taxonomy_path)
        instance = self.dataset.instances['instance-001']
        instance.label = None

        result = plotter.plot_dataset_tags_matrix('sidewalk geometry', 'sidewalk structure')

        self.assertGreater(result.data.size, 0)
        self.assertTrue((result.data.to_numpy() == 0).all())

    def test_plot_dataset_tags_matrix_prints_available_categories_when_none(self):
        plotter = SideSeeingPlotter(self.dataset, path_taxonomy=self.taxonomy_path)
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            result = plotter.plot_dataset_tags_matrix(None, 'sidewalk structure')

        self.assertIsNone(result)
        output = buffer.getvalue()
        self.assertIn('ERROR. You must pass a category name.', output)
        self.assertIn('sidewalk geometry', output)
        self.assertIn('sidewalk structure', output)

    def test_plot_instance_audio_extracts_audio_when_none(self):
        plotter = SideSeeingPlotter(self.dataset)
        instance = SimpleNamespace(video='video.mp4', audio=None)

        with patch(
            'sideseeing_tools.plot.media.extract_audio', return_value='video.wav'
        ) as extract_audio, patch(
            'sideseeing_tools.plot.media.load_audio_signal',
            side_effect=RuntimeError('stop after audio loading'),
        ) as load_audio:
            with self.assertRaisesRegex(RuntimeError, 'stop after audio loading'):
                plotter.plot_instance_audio(instance)

        extract_audio.assert_called_once_with('video.mp4', 'video.wav')
        load_audio.assert_called_once_with('video.wav')

    def test_plot_instance_audio_renders_waveform_and_spectrogram_without_librosa(self):
        plotter = SideSeeingPlotter(self.dataset)
        instance = self.dataset.instances['instance-001']

        with patch('sideseeing_tools.plot.plt.show') as show:
            plotter.plot_instance_audio(instance)

        show.assert_called_once()
        self.assertIsNotNone(instance.audio)
        if os.path.exists(instance.audio):
            os.remove(instance.audio)

    def test_plot_instance_video_frames_at_times_handles_single_time(self):
        plotter = SideSeeingPlotter(self.dataset)
        instance = self.dataset.instances['instance-001']

        with patch('sideseeing_tools.plot.plt.show') as show:
            plotter.plot_instance_video_frames_at_times(instance, times=[0.1])

        show.assert_called_once()

    def test_plot_sensors_handles_single_item(self):
        plotter = SideSeeingPlotter(self.dataset)
        df = pd.DataFrame({'Time (s)': [0.0, 1.0], 'x': [1.0, 2.0]})

        fig, axis = plotter.plot_sensors(
            [{'instance_name': 'instance-001', 'sensor_data': df}],
            'Time (s)',
            ['x'],
        )

        self.assertIsNotNone(fig)
        self.assertIsNotNone(axis)

    def test_plot_maps_pass_tiles_keyword_to_folium(self):
        plotter = SideSeeingPlotter(self.dataset)
        instance = self.dataset.instances['instance-001']

        with patch('folium.Map') as folium_map, patch('folium.Marker'), patch(
            'folium.LayerControl'
        ):
            plotter.plot_instance_map(instance, tiles='CartoDB positron', zoom_start=15)
            plotter.plot_dataset_map(tiles='CartoDB dark_matter', zoom_start=6)

        self.assertEqual(folium_map.call_count, 2)
        self.assertEqual(
            folium_map.call_args_list[0].kwargs,
            {'location': instance.geolocation_center, 'tiles': 'CartoDB positron', 'zoom_start': 15},
        )
        self.assertEqual(
            folium_map.call_args_list[1].kwargs['tiles'],
            'CartoDB dark_matter',
        )
        self.assertEqual(
            folium_map.call_args_list[1].kwargs['zoom_start'],
            6,
        )

    def test_inverse_geocode_uses_urllib_and_lazy_reverse_geocode(self):
        payload = io.BytesIO(
            b'{"results": [{"address_components": ['
            b'{"types": ["route"], "long_name": "Av. Paulista"},'
            b'{"types": ["administrative_area_level_2"], "long_name": "Sao Paulo"},'
            b'{"types": ["administrative_area_level_1"], "long_name": "SP"},'
            b'{"types": ["country"], "long_name": "Brazil"}'
            b']}]}'
        )
        payload.__enter__ = lambda *args: payload
        payload.__exit__ = lambda *args: False

        with patch('sideseeing_tools.geolocation.urlopen', return_value=payload) as mock_urlopen:
            google_res = geolocation.inverse_geocode(-23.56, -46.65, key='test-key')

        mock_urlopen.assert_called_once()
        self.assertEqual(
            google_res,
            {
                'country': 'Brazil',
                'state': 'SP',
                'city': 'Sao Paulo',
                'street': 'Av. Paulista',
            },
        )

        offline_res = geolocation.inverse_geocode(-23.56, -46.65)
        self.assertEqual(offline_res['country'], 'Brazil')

    def test_extract_gif_creates_gif_without_direct_imageio_import(self):
        instance = self.dataset.instances['instance-001']
        gif_path = instance.video.replace('.mp4', '.gif')

        try:
            if os.path.exists(gif_path):
                os.remove(gif_path)

            out = media.extract_gif(instance.video, gif_path, target_width=120, target_fps=2)
            self.assertEqual(out, gif_path)
            self.assertTrue(os.path.isfile(gif_path))
        finally:
            if os.path.exists(gif_path):
                os.remove(gif_path)



