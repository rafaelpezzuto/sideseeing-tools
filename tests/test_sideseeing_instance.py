import tempfile
import unittest

from pathlib import Path

from sideseeing_tools.constants import CONSUMPTION_SNIPPET_FILE_NAME, GPS_SNIPPET_FILE_NAME, ONE_AXIS_SNIPPET_FILE_NAME, THREE_AXES_SNIPPET_FILE_NAME, THREE_AXES_UNCALIBRATED_SNIPPET_FILE_NAME
from sideseeing_tools.sideseeing import SideSeeingDS


class TestSideSeeingInstance(unittest.TestCase):
    def setUp(self):
        self.dataset = SideSeeingDS('fixtures/dataset', name="Test Dataset")
        self.instance = self.dataset.instances['instance-001']

    def test_extract_snippet_gps_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = 0
            end_time = 2

            self.instance.extract_snippet(start_time, end_time, str(output_dir))

            gps_tmp_file = (output_dir / f"{GPS_SNIPPET_FILE_NAME.format(start_time, end_time)}")
            self.assertTrue(gps_tmp_file.exists())

            with open(gps_tmp_file, 'r') as f:
                self.assertEqual(
                    f.readline(), 
                    'datetime_utc,gps_interval,accuracy,latitude,longitude\n',
                )

                lines = sorted([l.strip() for l in f.readlines()])

                self.assertEqual(
                    len(lines), 
                    1,
                )

                unique_line = lines.pop(0)
                self.assertEqual(
                    unique_line,
                    '2024-01-06T15:00:05.104Z,15.0,21.932,-23.5395938,-46.7073943'
                )

    def test_extract_snippet_consumption_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = 0
            end_time = 2

            self.instance.extract_snippet(start_time, end_time, str(output_dir))

            consumption_tmp_file = (output_dir / f"{CONSUMPTION_SNIPPET_FILE_NAME.format(start_time, end_time)}")
            self.assertTrue(consumption_tmp_file.exists())

            with open(consumption_tmp_file, 'r') as f:
                self.assertEqual(
                    f.readline(), 
                    'datetime_utc,battery_microamperes\n',
                )

                lines = sorted([l.strip() for l in f.readlines()])

                self.assertEqual(
                    len(lines), 
                    3,
                )

                first = lines.pop(0)
                self.assertEqual(
                    first,
                    '2024-01-06T14:59:49.136Z,-767000.0'
                )

                last = lines.pop()
                self.assertEqual(
                    last,
                    '2024-01-06T14:59:51.135Z,-995000.0'
                )

    def test_extract_snippet_video_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            start_time = 0
            end_time = 2
            
            self.instance.extract_snippet(start_time, end_time, str(output_dir))

            video_tmp_file = (output_dir / f"video.{start_time}_{end_time}.mp4")
            self.assertTrue(video_tmp_file.exists())

    def test_extract_snippet_sensors1_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = 0
            end_time = 2

            self.instance.extract_snippet(start_time, end_time, str(output_dir))

            sensors1_tmp_file = (output_dir / f"{ONE_AXIS_SNIPPET_FILE_NAME.format(start_time, end_time)}")
            self.assertTrue(sensors1_tmp_file.exists())

            with open(sensors1_tmp_file, 'r') as f:
                self.assertEqual(
                    f.readline(), 
                    'timestamp_nano,datetime_utc,name,axis_x,accuracy\n',
                )

                lines = sorted([l.strip() for l in f.readlines()])

                self.assertEqual(
                    len(lines), 
                    2,
                )

                first = lines.pop(0)
                self.assertEqual(
                    first,
                    '551845494422,2024-01-06T14:59:48.593Z,tcs3720 ambient light sensor non-wakeup,3456.75,3',
                )

                last = lines.pop()
                self.assertEqual(
                    last,
                    '552845337651,2024-01-06T14:59:49.593Z,tcs3720 ambient light sensor non-wakeup,3989.5,3'
                )

    def test_extract_snippet_sensors3_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = 0
            end_time = 2

            self.instance.extract_snippet(start_time, end_time, str(output_dir))

            sensors3_tmp_file = (output_dir / f"{THREE_AXES_SNIPPET_FILE_NAME.format(start_time, end_time)}")
            self.assertTrue(sensors3_tmp_file.exists())

            with open(sensors3_tmp_file, 'r') as f:
                self.assertEqual(
                    f.readline(), 
                    'timestamp_nano,datetime_utc,name,axis_x,axis_y,axis_z,accuracy\n',
                )

                lines = sorted([l.strip() for l in f.readlines()])

                self.assertEqual(
                    len(lines), 
                    200,
                )

                first = lines.pop(0)
                self.assertEqual(
                    first,
                    '551390736558,2024-01-06T14:59:48.138Z,icm4x6xx accelerometer non-wakeup,8.803479,-0.51116204,3.3363202,3',
                )

                last = lines.pop()
                self.assertEqual(
                    last,
                    '553577475724,2024-01-06T14:59:50.326Z,gravity  wakeup,8.93816,-0.47404757,4.0068645,3'
                )

    def test_extract_snippet_sensors6_is_ok(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = 0
            end_time = 2

            self.instance.extract_snippet(start_time, end_time, str(output_dir))

            sensors6_tmp_file = (output_dir / f"{THREE_AXES_UNCALIBRATED_SNIPPET_FILE_NAME.format(start_time, end_time)}")
            self.assertTrue(sensors6_tmp_file.exists())

            with open(sensors6_tmp_file, 'r') as f:
                self.assertEqual(
                    f.readline(), 
                    'timestamp_nano,datetime_utc,name,axis_x,axis_y,axis_z,delta_x,delta_y,delta_z,accuracy\n',
                )

                lines = sorted([l.strip() for l in f.readlines()])

                self.assertEqual(
                    len(lines), 
                    44,
                )

                first = lines.pop(0)
                self.assertEqual(
                    first,
                    '551555800880,2024-01-06T14:59:48.303Z,icm4x6xx gyroscope-uncalibrated wakeup,0.09440899,-0.01238369,0.026232118,0.09440899,-0.01238369,0.026232118,3',
                )

                last = lines.pop()
                self.assertEqual(
                    last,
                    '553551816870,2024-01-06T14:59:50.299Z,icm4x6xx gyroscope-uncalibrated non-wakeup,0.035553172,0.018508956,0.01890843,0.035553172,0.018508956,0.01890843,3'
                )

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