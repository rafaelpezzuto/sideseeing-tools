import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from sideseeing_tools import archives, exceptions
from sideseeing_tools.sideseeing import SideSeeingDS


class TestSideSeeingDS(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../fixtures/dataset/'))


    def test_sideseeingds_initialization(self):
        ds = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")
        self.assertEqual(ds.name, "TestDataset")
        self.assertEqual(ds.root_dir, f"{self.root_dir}{os.path.sep}")
        self.assertEqual(ds.size, 1)

        with self.assertRaises(exceptions.RootDirIsNotADirectoryError):
            SideSeeingDS(root_dir=os.path.join(self.root_dir, "taxonomy.csv"))

        with self.assertRaises(exceptions.RootDirIsNotADirectoryError):
            SideSeeingDS(root_dir=os.path.join(self.root_dir, "/non_existent"))

    def test_sideseeingds_metadata(self):
        ds = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")

        self.assertIsNotNone(ds.metadata())


    def test_sideseeingds_str_repr(self):
        ds = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")

        self.assertEqual(str(ds), "SSDS[name: TestDataset, instances: 1]")
        self.assertEqual(repr(ds), "SSDS[name: TestDataset, instances: 1]")

    def test_populate_sensors_handles_none_sensors(self):
        ds = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")
        instance = ds.instances['instance-001']
        instance.sensors1 = None

        ds.populate_sensors()
        self.assertIn('sensors1', ds.sensors)
        self.assertEqual(ds.sensors['sensors1'], {})

    def test_accepts_pathlib_path(self):
        ds = SideSeeingDS(root_dir=Path(self.root_dir), name="TestDataset")

        self.assertEqual(ds.size, 1)

    def test_loads_single_zip_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / 'captured-sample.zip'
            instance_dir = Path(self.root_dir) / 'instance-001'

            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.write(instance_dir / 'metadata.json', 'metadata.json')
                archive.write(instance_dir / 'labels.txt', 'labels.txt')

            ds = SideSeeingDS(root_dir=archive_path, name="ZipDataset")

            self.assertEqual(ds.size, 1)
            self.assertIn('captured-sample', ds.instances)
            self.assertEqual(len(ds.instances['captured-sample'].label), 20)

    def test_loads_zips_from_nested_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            route_dir = root_dir / 'City' / 'Route01-a'
            route_dir.mkdir(parents=True)
            archive_path = route_dir / 'capture-001.zip'
            metadata_path = Path(self.root_dir) / 'instance-001' / 'metadata.json'

            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.write(metadata_path, 'metadata.json')

            ds = SideSeeingDS(root_dir=root_dir, subdir_data=Path('City'), name="NestedZipDataset")

            self.assertEqual(ds.size, 1)
            self.assertIn('Route01-a_capture-001', ds.instances)

    def test_rejects_unsafe_zip_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / 'unsafe.zip'

            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr('../metadata.json', '{}')

            with self.assertRaisesRegex(ValueError, 'Unsafe path in ZIP archive'):
                SideSeeingDS(root_dir=archive_path, name="UnsafeZipDataset")

    def test_rejects_unsafe_archive_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / 'capture.zip'

            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr('metadata.json', '{}')

            with self.assertRaisesRegex(ValueError, 'Unsafe archive destination'):
                archives.extract_dataset_archive(archive_path, temp_dir, '../outside')

    def test_rejects_identifier_collision_between_directory_and_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            directory = root / 'capture'
            directory.mkdir()
            source = Path(self.root_dir) / 'instance-001' / 'metadata.json'
            (directory / 'metadata.json').write_bytes(source.read_bytes())
            with zipfile.ZipFile(root / 'capture.zip', 'w') as archive:
                archive.write(source, 'metadata.json')

            with self.assertRaisesRegex(ValueError, 'Duplicate recording identifier'):
                SideSeeingDS(root)

    def test_zip_files_remain_available_when_only_instance_is_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / 'capture.zip'
            source = Path(self.root_dir) / 'instance-001' / 'metadata.json'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.write(source, 'metadata.json')

            instance = next(SideSeeingDS(archive_path).iterator)

            self.assertTrue(Path(instance.files['metadata'].file_path).is_file())
            self.assertEqual(Path(instance.files['metadata'].file_path).read_bytes(), source.read_bytes())
