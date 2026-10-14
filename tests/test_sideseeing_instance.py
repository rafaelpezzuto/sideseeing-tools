import json
import tempfile
import unittest

from pathlib import Path

import pandas as pd

from sideseeing_tools.constants import GPS_SNIPPET_FILE_NAME, ONE_AXIS_SNIPPET_FILE_NAME
from sideseeing_tools.sideseeing import SideSeeingDS


class TestSideSeeingInstance(unittest.TestCase):
    def setUp(self):
        self.dataset = SideSeeingDS('fixtures/dataset', name="Test Dataset")
        self.instance = self.dataset.instances['instance-001']

    def test_extract_snippet_with_include_time_span_on_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            timestamped = Path(temp_dir) / 'timestamped'
            standard = Path(temp_dir) / 'standard'
            self.instance.extract_snippet(0, 2, timestamped, include_time_span_on_filename=True)
            self.instance.extract_snippet(0, 2, standard)
            for filename in ['gps', 'sensors.one', 'sensors.three', 'sensors.three.uncalibrated']:
                self.assertTrue((timestamped / f'{filename}.0_2.csv').is_file())
                self.assertTrue((standard / f'{filename}.csv').is_file())
            self.assertEqual(SideSeeingDS(timestamped).size, 1)
            self.assertEqual(SideSeeingDS(standard).size, 1)

    def _assert_snippet_preserves_utc_rows(self, attribute, start, end):
        origin = pd.Timestamp(self.instance.media_start_time)
        stop = self.instance.media_total_time if end < 0 else end
        first = origin + pd.to_timedelta(start, unit='s')
        last = origin + pd.to_timedelta(stop, unit='s')
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'snippet'
            self.instance.extract_snippet(start, end, destination, include_time_span_on_filename=True)
            reloaded = next(SideSeeingDS(destination).iterator)
            source = getattr(self.instance, attribute)
            actual = getattr(reloaded, attribute)
            source_frames = source if isinstance(source, dict) else {attribute: source}
            actual_frames = actual if isinstance(actual, dict) else {attribute: actual}
            for name, frame in source_frames.items():
                expected = frame.loc[(frame['Datetime UTC'] >= first) & (frame['Datetime UTC'] < last)]
                if expected.empty:
                    continue
                self.assertIn(name, actual_frames)
                pd.testing.assert_frame_equal(expected.drop(columns='Time (s)').reset_index(drop=True),
                                              actual_frames[name].drop(columns='Time (s)').reset_index(drop=True),
                                              check_dtype=False)

    def test_extract_snippet_metadata_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = 0
            end_time = 2

            self.instance.extract_snippet(start_time, end_time, str(output_dir), True)

            metadata_tmp_file = (output_dir / f"metadata.{start_time}_{end_time}.json")
            self.assertTrue(metadata_tmp_file.exists())

            with open(metadata_tmp_file, 'r') as f:
                metadata = json.load(f)

                snippet = metadata['snippet']

                self.assertIn('start_time', snippet)
                self.assertIn('end_time', snippet)
                self.assertIn('total_time', snippet)
                self.assertEqual(snippet['start_time'], start_time)
                self.assertEqual(snippet['end_time'], end_time)
                self.assertEqual(snippet['total_time'], end_time - start_time)

    def test_extract_snippet_gps_is_ok(self):
        self._assert_snippet_preserves_utc_rows('geolocation_points', 0, 2)

    def test_extract_snippet_gps_with_end_time_minus_one_is_ok(self):
        self._assert_snippet_preserves_utc_rows('geolocation_points', 57, -1)

    def test_extract_snippet_consumption_is_ok(self):
        self._assert_snippet_preserves_utc_rows('consumption', 0, 2)

    def test_extract_snippet_consumption_with_end_time_minus_one_is_ok(self):
        self._assert_snippet_preserves_utc_rows('consumption', 0, -1)

    def test_extract_snippet_video_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            start_time = 0
            end_time = 2
            
            self.instance.extract_snippet(start_time, end_time, str(output_dir), True)

            video_tmp_file = (output_dir / f"video.{start_time}_{end_time}.mp4")
            self.assertTrue(video_tmp_file.exists())

    def test_extract_snippet_sensors1_is_ok(self):
        self._assert_snippet_preserves_utc_rows('sensors1', 0, 2)

    def test_extract_snippet_sensors3_is_ok(self):
        self._assert_snippet_preserves_utc_rows('sensors3', 0, 2)

    def test_extract_snippet_sensors3_with_end_time_minus_one_is_ok(self):
        self._assert_snippet_preserves_utc_rows('sensors3', 0, -1)

    def test_extract_snippet_sensors6_is_ok(self):
        self._assert_snippet_preserves_utc_rows('sensors6', 0, 2)

    def test_extract_frames_in_memory_is_ok(self):
        frames = self.instance.extract_frames(step=30, prefix='frame_')
        self.assertGreater(len(frames), 0)

    def test_extract_frames_at_times_in_memory_is_ok(self):
        frame_times = [1.0, 2.0, 3.0]
        frames = self.instance.extract_frames_at_times(frame_times, prefix='frame_')
        self.assertEqual(len(frames), len(frame_times))

    def test_extract_frames_at_positions_in_memory_is_ok(self):
        frame_positions = [30, 60, 90]
        frames = self.instance.extract_frames_at_positions(frame_positions, prefix='frame_')
        self.assertEqual(len(frames), len(frame_positions))

    def test_extract_frames_timespan_in_memory_is_ok(self):
        start_time = 1.0
        end_time = 3.0
        frames = self.instance.extract_frames_timespan(start_time, end_time, step=30, prefix='frame_')
        self.assertGreater(len(frames), 0)

    def test_extract_frames_positionspan_in_memory_is_ok(self):
        start_frame = 30
        end_frame = 90
        frames = self.instance.extract_frames_positionspan(start_frame, end_frame, step=30, prefix='frame_')
        self.assertGreater(len(frames), 0)

    def test_extract_snippet_with_none_sensors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            original_sensors1 = self.instance.sensors1
            self.instance.sensors1 = None

            try:
                self.instance.extract_snippet(0, 2, str(output_dir), include_time_span_on_filename=True)
                sensors1_file = output_dir / f"{ONE_AXIS_SNIPPET_FILE_NAME.format(0, 2)}"
                self.assertFalse(sensors1_file.exists())
            finally:
                self.instance.sensors1 = original_sensors1

    def test_extract_snippet_with_string_time_bounds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            self.instance.extract_snippet("0", "2", str(output_dir), include_time_span_on_filename=True)
            gps_file = output_dir / f"{GPS_SNIPPET_FILE_NAME.format(0, 2)}"
            self.assertTrue(gps_file.exists())

    def test_invalid_time_bounds_do_not_create_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'snippet'

            with self.assertRaises(ValueError):
                self.instance.extract_snippet('invalid', '2', str(output_dir))

            self.assertFalse(output_dir.exists())

    def test_nonfinite_negative_and_reversed_bounds_do_not_write_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'snippet'
            for start, end in [(float('nan'), 2), (0, float('inf')), (-1, 2), (2, 1), (1, 1)]:
                with self.subTest(start=start, end=end):
                    with self.assertRaises(ValueError):
                        self.instance.extract_snippet(start, end, str(output_dir))
                    self.assertFalse(output_dir.exists())

    def test_calculate_distance_does_not_mutate_geolocation_points(self):
        original = self.instance.geolocation_points.copy(deep=True)

        self.instance.calculate_sample_distance_traveled()

        pd.testing.assert_frame_equal(self.instance.geolocation_points, original)
