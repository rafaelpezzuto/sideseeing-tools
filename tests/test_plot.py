import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sideseeing_tools.plot import SideSeeingPlotter
from sideseeing_tools.sideseeing import SideSeeingDS


class TestSideSeeingPlotter(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/'))
        self.dataset = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")
        self.taxonomy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/taxonomy.csv'))

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
