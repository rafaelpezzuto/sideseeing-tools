import os
import unittest

from sideseeing_tools.sideseeing import SideSeeingDS
from sideseeing_tools import exceptions


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

    def test_sideseeingds_properties(self):
        ds = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")
        self.assertEqual(ds.size, 1)

    def test_sideseeingds_str_repr(self):
        ds = SideSeeingDS(root_dir=self.root_dir, name="TestDataset")

        self.assertEqual(str(ds), "SSDS[name: TestDataset, instances: 1]")
        self.assertEqual(repr(ds), "SSDS[name: TestDataset, instances: 1]")
