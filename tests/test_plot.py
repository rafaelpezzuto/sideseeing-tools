import io
import os
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib.pyplot as plt
import pandas as pd

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

        with patch('sideseeing_tools.plot.librosa') as librosa:
            with patch('sideseeing_tools.plot.media.extract_audio', return_value='video.wav') as extract_audio:
                librosa.load.side_effect = RuntimeError('stop after audio loading')

                with self.assertRaisesRegex(RuntimeError, 'stop after audio loading'):
                    plotter.plot_instance_audio(instance)

        extract_audio.assert_called_once_with('video.mp4', 'video.wav')
        librosa.load.assert_called_once_with('video.wav')

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

        with patch('sideseeing_tools.plot.folium.Map') as folium_map, patch(
            'sideseeing_tools.plot.folium.Marker'
        ), patch('sideseeing_tools.plot.folium.LayerControl'):
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
