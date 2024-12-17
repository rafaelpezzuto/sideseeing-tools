import os
import tempfile
import unittest

from sideseeing_tools.media import (
    extract_frames_at_times,
    extract_frames_at_positions,
    extract_frames,
    extract_frames_timespan,
    extract_frames_positionspan,
)


class TestExtractFramesAtTimes(unittest.TestCase):

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp()
        os.makedirs(self.tmp_path, exist_ok=True)
        self.video_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/instance-001/video.mp4'))

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            for file in os.listdir(self.tmp_path):
                os.remove(os.path.join(self.tmp_path, file))
            os.rmdir(self.tmp_path)

    def test_extract_frames_at_times_success(self):
        frame_times = [1.0, 36.0, 59.8]
        prefix = "frame_"
        extract_frames_at_times(self.video_file, frame_times, target_dir=self.tmp_path, prefix=prefix)
        for time in frame_times:
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_at_times_memory_success(self):
        frame_times = [1.0, 36.0, 59.8]
        prefix = "frame_"
        frames = extract_frames_at_times(self.video_file, frame_times, prefix=prefix)
        self.assertEqual(len(frames), len(frame_times))

    def test_extract_frames_at_times_invalid_times(self):
        frame_times = [120.0, 1000.0]
        prefix = "frame_"
        extract_frames_at_times(self.video_file, frame_times, target_dir=self.tmp_path, prefix=prefix)
        for time in frame_times:
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_at_times_invalid_file(self):
        frame_times = [1.0, 2.0, 3.0]
        prefix = "frame_"
        extract_frames_at_times("invalid_path.mp4", frame_times, target_dir=self.tmp_path, prefix=prefix)
        for time in frame_times:
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_at_times_no_prefix(self):
        frame_times = [1.0, 20.0, 33.0]
        extract_frames_at_times(self.video_file, frame_times, target_dir=self.tmp_path)
        for time in frame_times:
            frame_number = int(time * 30.0)
            frame_name = f'{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_at_times_custom_left_zeros(self):
        frame_times = [1.0, 28.0, 69.0]
        prefix = "frame_"
        left_zeros = 3
        extract_frames_at_times(self.video_file, frame_times, target_dir=self.tmp_path, prefix=prefix, left_zeros=left_zeros)
        for time in frame_times:
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(left_zeros)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))


class TestExtractFramesAtPositions(unittest.TestCase):

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp()
        os.makedirs(self.tmp_path, exist_ok=True)
        self.video_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/instance-001/video.mp4'))

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            for file in os.listdir(self.tmp_path):
                os.remove(os.path.join(self.tmp_path, file))
            os.rmdir(self.tmp_path)

    def test_extract_frames_at_positions_success(self):
        frame_positions = [1, 2, 3]
        prefix = "frame_"
        extract_frames_at_positions(self.video_file, frame_positions, target_dir=self.tmp_path, prefix=prefix)
        for pos in frame_positions:
            frame_name = f'{prefix}{str(pos).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_at_positions_invalid_positions(self):
        frame_positions = [10000, 22000]
        prefix = "frame_"
        extract_frames_at_positions(self.video_file, frame_positions, target_dir=self.tmp_path, prefix=prefix)
        for pos in frame_positions:
            frame_name = f'{prefix}{str(pos).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_at_positions_invalid_file(self):
        frame_positions = [1, 2, 3]
        prefix = "frame_"
        extract_frames_at_positions("invalid_path.mp4", frame_positions, target_dir=self.tmp_path, prefix=prefix)
        for pos in frame_positions:
            frame_name = f'{prefix}{str(pos).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_at_positions_no_prefix(self):
        frame_positions = [1, 2, 3]
        extract_frames_at_positions(self.video_file, frame_positions, target_dir=self.tmp_path)
        for pos in frame_positions:
            frame_name = f'{str(pos).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_at_positions_custom_left_zeros(self):
        frame_positions = [1, 2, 3]
        prefix = "frame_"
        left_zeros = 3
        extract_frames_at_positions(self.video_file, frame_positions, target_dir=self.tmp_path, prefix=prefix, left_zeros=left_zeros)
        for pos in frame_positions:
            frame_name = f'{prefix}{str(pos).zfill(left_zeros)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))
            
            
class TestExtractFramesTimespan(unittest.TestCase):

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp()
        os.makedirs(self.tmp_path, exist_ok=True)
        self.video_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/instance-001/video.mp4'))

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            for file in os.listdir(self.tmp_path):
                os.remove(os.path.join(self.tmp_path, file))
            os.rmdir(self.tmp_path)

    def test_extract_frames_timespan_success(self):
        start_time = 1.0
        end_time = 3.0
        prefix = "frame_"
        extract_frames_timespan(self.video_file, start_time, end_time, target_dir=self.tmp_path, prefix=prefix)
        for time in range(int(start_time), int(end_time)):
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_timespan_invalid_times(self):
        start_time = 150.0
        end_time = 200.0
        prefix = "frame_"
        extract_frames_timespan(self.video_file, start_time, end_time, target_dir=self.tmp_path, prefix=prefix)
        for time in range(int(start_time), int(end_time)):
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_timespan_invalid_file(self):
        start_time = 1.0
        end_time = 3.0
        prefix = "frame_"
        extract_frames_timespan("invalid_path.mp4", start_time, end_time, target_dir=self.tmp_path, prefix=prefix)
        for time in range(int(start_time), int(end_time)):
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_timespan_no_prefix(self):
        start_time = 1.0
        end_time = 3.0
        extract_frames_timespan(self.video_file, start_time, end_time, target_dir=self.tmp_path)
        for time in range(int(start_time), int(end_time)):
            frame_number = int(time * 30.0)
            frame_name = f'{str(frame_number).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_timespan_custom_left_zeros(self):
        start_time = 1.0
        end_time = 3.0
        prefix = "frame_"
        left_zeros = 3
        extract_frames_timespan(self.video_file, start_time, end_time, target_dir=self.tmp_path, prefix=prefix, left_zeros=left_zeros)
        for time in range(int(start_time), int(end_time)):
            frame_number = int(time * 30.0)
            frame_name = f'{prefix}{str(frame_number).zfill(left_zeros)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))
            
            
class TestExtractFrames(unittest.TestCase):

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp()
        os.makedirs(self.tmp_path, exist_ok=True)
        self.video_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/instance-001/video.mp4'))

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            for file in os.listdir(self.tmp_path):
                os.remove(os.path.join(self.tmp_path, file))
            os.rmdir(self.tmp_path)

    def test_extract_frames_success(self):
        prefix = "frame_"
        frames_paths = extract_frames(self.video_file, target_dir=self.tmp_path, prefix=prefix)
        step = 30
        last_frame = len(frames_paths) * step
        for i in range(0, last_frame, step):
            frame_name = f'{prefix}{str(i).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_invalid_file(self):
        prefix = "frame_"
        extract_frames("invalid_path.mp4", target_dir=self.tmp_path, prefix=prefix)
        for i in range(60):
            frame_name = f'{prefix}{str(i).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_no_prefix(self):
        frames_paths = extract_frames(self.video_file, target_dir=self.tmp_path)
        step = 30
        last_frame = len(frames_paths) * step
        for i in range(0, last_frame, step):
            frame_name = f'{str(i).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_custom_left_zeros(self):
        prefix = "frame_"
        left_zeros = 3
        frames_paths = extract_frames(self.video_file, target_dir=self.tmp_path, prefix=prefix, left_zeros=left_zeros)
        step = 30
        last_frame = len(frames_paths) * step
        for i in range(0, last_frame, step):
            frame_name = f'{prefix}{str(i).zfill(left_zeros)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_custom_step(self):
        prefix = "frame_"
        custom_step = 15
        extract_frames(self.video_file, target_dir=self.tmp_path, step=custom_step, prefix=prefix)
        for i in range(0, 60, custom_step):
            frame_name = f'{prefix}{str(i).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))


class TestExtractFramesPositionspan(unittest.TestCase):

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp()
        os.makedirs(self.tmp_path, exist_ok=True)
        self.video_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/instance-001/video.mp4'))

    def tearDown(self):
        if os.path.exists(self.tmp_path):
            for file in os.listdir(self.tmp_path):
                os.remove(os.path.join(self.tmp_path, file))
            os.rmdir(self.tmp_path)

    def test_extract_frames_positionspan_success(self):
        start_frame = 1
        end_frame = 30
        prefix = "frame_"
        extract_frames_positionspan(self.video_file, start_frame, end_frame, target_dir=self.tmp_path, step=1, prefix=prefix)
        for frame in range(start_frame, end_frame):
            frame_name = f'{prefix}{str(frame).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_positionspan_invalid_positions(self):
        start_frame = 10000
        end_frame = 20000
        prefix = "frame_"
        extract_frames_positionspan(self.video_file, start_frame, end_frame, target_dir=self.tmp_path, prefix=prefix)
        for frame in range(start_frame, end_frame):
            frame_name = f'{prefix}{str(frame).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_positionspan_invalid_file(self):
        start_frame = 1
        end_frame = 30
        prefix = "frame_"
        extract_frames_positionspan("invalid_path.mp4", start_frame, end_frame, target_dir=self.tmp_path, prefix=prefix)
        for frame in range(start_frame, end_frame):
            frame_name = f'{prefix}{str(frame).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertFalse(os.path.exists(frame_path))

    def test_extract_frames_positionspan_no_prefix(self):
        start_frame = 1
        end_frame = 30
        extract_frames_positionspan(self.video_file, start_frame, end_frame, target_dir=self.tmp_path, step=1)
        for frame in range(start_frame, end_frame):
            frame_name = f'{str(frame).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_positionspan_custom_left_zeros(self):
        start_frame = 1
        end_frame = 30
        prefix = "frame_"
        left_zeros = 3
        extract_frames_positionspan(self.video_file, start_frame, end_frame, target_dir=self.tmp_path, step=1, prefix=prefix, left_zeros=left_zeros)
        for frame in range(start_frame, end_frame):
            frame_name = f'{prefix}{str(frame).zfill(left_zeros)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))

    def test_extract_frames_positionspan_custom_step(self):
        start_frame = 1
        end_frame = 30
        prefix = "frame_"
        custom_step = 2
        extract_frames_positionspan(self.video_file, start_frame, end_frame, target_dir=self.tmp_path, step=custom_step, prefix=prefix)
        for frame in range(start_frame, end_frame, custom_step):
            frame_name = f'{prefix}{str(frame).zfill(5)}.jpg'
            frame_path = os.path.join(self.tmp_path, frame_name)
            self.assertTrue(os.path.exists(frame_path))
