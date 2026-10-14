import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import pandas as pd

from sideseeing_tools.constants import DATETIME_UTC_FORMAT
from sideseeing_tools.utils import (
    extract_dataframe_snippet,
    generate_metadata,
    load_csv_data,
    parse_wcdma,
)


class TestParseWcdma(unittest.TestCase):
    def test_parse_wcdma_specific_case_1(self):
        """Test parsing specific WCDMA data case 1 with Claro (America Movil)."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-71 ber=2147483647 rscp=-120 ecno=-24 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 36211,
            'cid': 190805339,
            'psc': 350,
            'uarfcn': 4437,
            'mcc': 724,
            'mnc': 5,
            'alpha_long': 'Claro (America Movil)',
            'alpha_short': 'Claro',
            'ss': -71,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 4
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_specific_case_2(self):
        """Test parsing specific WCDMA data case 2 with null MCC/MNC values."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-71 ber=2147483647 rscp=-120 ecno=-24 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 2147483647,
            'cid': 2147483647,
            'psc': 350,
            'uarfcn': 4414,
            'alpha_long': '',
            'alpha_short': '',
            'ss': -71,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 4
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_specific_case_3(self):
        """Test parsing specific WCDMA data case 3 with PSC 342 and level 3."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=342 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-79 ber=2147483647 rscp=-120 ecno=-24 level=3}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 2147483647,
            'cid': 2147483647,
            'psc': 342,
            'uarfcn': 4414,
            'alpha_long': '',
            'alpha_short': '',
            'ss': -79,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 3
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_specific_case_4(self):
        """Test parsing specific WCDMA data case 4 with PSC 419 and ss -83."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=419 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-83 ber=2147483647 rscp=-120 ecno=-24 level=3}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 2147483647,
            'cid': 2147483647,
            'psc': 419,
            'uarfcn': 4414,
            'alpha_long': '',
            'alpha_short': '',
            'ss': -83,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 3
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_specific_case_5(self):
        """Test parsing specific WCDMA data case 5 with PSC 277."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=277 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-83 ber=2147483647 rscp=-120 ecno=-24 level=3}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 2147483647,
            'cid': 2147483647,
            'psc': 277,
            'uarfcn': 4414,
            'alpha_long': '',
            'alpha_short': '',
            'ss': -83,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 3
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_specific_case_6(self):
        """Test parsing specific WCDMA data case 6 with PSC 426."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=426 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-83 ber=2147483647 rscp=-120 ecno=-24 level=3}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 2147483647,
            'cid': 2147483647,
            'psc': 426,
            'uarfcn': 4414,
            'alpha_long': '',
            'alpha_short': '',
            'ss': -83,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 3
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_specific_case_7(self):
        """Test parsing specific WCDMA data case 7 with UARFCN 10638 and level 1."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=677579659304ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-101 ber=2147483647 rscp=-120 ecno=-24 level=1}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 677579659304,
            'connection_status': 0,
            'lac': 2147483647,
            'cid': 2147483647,
            'psc': 379,
            'uarfcn': 10638,
            'alpha_long': '',
            'alpha_short': '',
            'ss': -101,
            'ber': 2147483647,
            'rscp': -120,
            'ecno': -24,
            'level': 1
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_multiple_cases(self):
        cases = [
            '2025-03-24T01:56:56.704Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=19839469731ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190835977 mPsc=350 mUarfcn=4414 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-69 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:56:57.753Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:56:57.753Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:56:57.753Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:56:58.791Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:56:58.791Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:56:58.791Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:56:59.824Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:56:59.824Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:56:59.824Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:00.854Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:00.854Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:00.854Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=361570945587ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:01.895Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:01.895Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:01.895Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:02.935Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:02.935Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:02.935Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:03.974Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:03.974Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:03.974Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:05.013Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:05.013Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:05.013Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:06.031Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:06.031Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:06.031Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=366575698085ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:07.071Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=371580375167ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=350 mUarfcn=4414 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-61 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:07.071Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=371580375167ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=2147483647 mCid=2147483647 mPsc=379 mUarfcn=10638 mMcc=null mMnc=null mAlphaLong= mAlphaShort= mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-107 ber=2147483647 rscp=-120 ecno=-24 level=1}'
            '2025-03-24T01:57:07.071Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=371580375167ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-65 ber=2147483647 rscp=-120 ecno=-24 level=4}'
            '2025-03-24T01:57:08.118Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=371580375167ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro (America Movil) mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-65 ber=2147483647 rscp=-120 ecno=-24 level=4}'
        ]

        for case in cases:
            with self.subTest(case=case):
                result = parse_wcdma(case)
                self.assertIsInstance(result, dict)
                self.assertIn('registered', result)
                self.assertIn('timestamp', result)
                self.assertIn('connection_status', result)
                self.assertIn('lac', result)
                self.assertIn('cid', result)
                self.assertIn('psc', result)
                self.assertIn('uarfcn', result)
                self.assertIn('mcc', result)
                self.assertIn('mnc', result)
                self.assertIn('alpha_long', result)
                self.assertIn('alpha_short', result)
                self.assertIn('ss', result)
                self.assertIn('ber', result)
                self.assertIn('rscp', result)
                self.assertIn('ecno', result)
                self.assertIn('level', result)

    def test_parse_wcdma_real_world_claro_data_variant1(self):
        """Test parsing real world WCDMA data from Claro BRA network."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=1216026640994ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190835976 mPsc=342 mUarfcn=4414 mMcc=724 mMnc=05 mAlphaLong=Claro BRA mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-63 ber=99 rscp=-63 ecno=-6 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 1216026640994,
            'connection_status': 0,
            'lac': 36211,
            'cid': 190835976,
            'psc': 342,
            'uarfcn': 4414,
            'mcc': 724,
            'mnc': 5,
            'alpha_long': 'Claro BRA',
            'alpha_short': 'Claro',
            'ss': -63,
            'ber': 99,
            'rscp': -63,
            'ecno': -6,
            'level': 4
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_real_world_claro_data_variant2(self):
        """Test parsing real world WCDMA data with different signal values."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=1216026640994ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190835976 mPsc=342 mUarfcn=4414 mMcc=724 mMnc=05 mAlphaLong=Claro BRA mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-69 ber=99 rscp=-68 ecno=-6 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 1216026640994,
            'connection_status': 0,
            'lac': 36211,
            'cid': 190835976,
            'psc': 342,
            'uarfcn': 4414,
            'mcc': 724,
            'mnc': 5,
            'alpha_long': 'Claro BRA',
            'alpha_short': 'Claro',
            'ss': -69,
            'ber': 99,
            'rscp': -68,
            'ecno': -6,
            'level': 4
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_different_timestamp(self):
        """Test parsing WCDMA data with different timestamp."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=1226044812687ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190835976 mPsc=342 mUarfcn=4414 mMcc=724 mMnc=05 mAlphaLong=Claro BRA mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-67 ber=99 rscp=-66 ecno=-7 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 1226044812687,
            'connection_status': 0,
            'lac': 36211,
            'cid': 190835976,
            'psc': 342,
            'uarfcn': 4414,
            'mcc': 724,
            'mnc': 5,
            'alpha_long': 'Claro BRA',
            'alpha_short': 'Claro',
            'ss': -67,
            'ber': 99,
            'rscp': -66,
            'ecno': -7,
            'level': 4
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_different_cell_id(self):
        """Test parsing WCDMA data with different cell ID and PSC."""
        cell_info = "CellInfoWcdma:{mRegistered=NO mTimeStamp=2014554806811ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro BRA mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-57 ber=99 rscp=-56 ecno=-5 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'timestamp': 2014554806811,
            'connection_status': 0,
            'lac': 36211,
            'cid': 190805339,
            'psc': 350,
            'uarfcn': 4437,
            'mcc': 724,
            'mnc': 5,
            'alpha_long': 'Claro BRA',
            'alpha_short': 'Claro',
            'ss': -57,
            'ber': 99,
            'rscp': -56,
            'ecno': -5,
            'level': 4
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_mnc_with_leading_zero(self):
        """Test parsing WCDMA data with MNC containing leading zero."""
        cell_info = "mMcc=724 mMnc=05"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'mcc': 724,
            'mnc': 5
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_complex_alpha_fields(self):
        """Test parsing WCDMA data with complex alpha long field containing spaces."""
        cell_info = "{mAlphaLong=Claro BRA mAlphaShort=Claro}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'alpha_long': 'Claro BRA',
            'alpha_short': 'Claro'
        }
        
        self.assertEqual(result, expected)

    def test_parse_wcdma_varying_signal_strengths(self):
        """Test parsing WCDMA data with varying signal strength values."""
        test_cases = [
            ("ss=-63 rscp=-63 ecno=-6", {'ss': -63, 'rscp': -63, 'ecno': -6}),
            ("ss=-69 rscp=-68 ecno=-6", {'ss': -69, 'rscp': -68, 'ecno': -6}),
            ("ss=-67 rscp=-66 ecno=-7", {'ss': -67, 'rscp': -66, 'ecno': -7}),
            ("ss=-71 rscp=-71 ecno=-7", {'ss': -71, 'rscp': -71, 'ecno': -7}),
            ("ss=-57 rscp=-56 ecno=-5", {'ss': -57, 'rscp': -56, 'ecno': -5}),
            ("ss=-61 rscp=-61 ecno=-5", {'ss': -61, 'rscp': -61, 'ecno': -5})
        ]
        
        for cell_info, expected in test_cases:
            with self.subTest(cell_info=cell_info):
                result = parse_wcdma(cell_info)
                self.assertEqual(result, expected)

    def test_parse_wcdma_malformed_data(self):
        """Test parsing malformed WCDMA data with extra brackets and nested structures."""
        cell_info = "CellInfoWcdma:{mRegistered=NO CellIdentityWcdma:{ mLac=36211 mCid=190835976} CellSignalStrengthWcdma: ss=-63 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'lac': 36211,
            'cid': 190835976,
            'ss': -63,
            'level': 4
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_wcdma_complete_data(self):
        """Test parsing WCDMA string with all fields present."""
        cell_info = "{mRegistered=Yes mTimeStamp=1234567890ns mCellConnectionStatus=1 mLac=12345 mCid=67890 mPsc=123 mUarfcn=456 mMcc=310 mMnc=260 mAlphaLong=Verizon mAlphaShort=VZW ss=-85 ber=99 rscp=-75 ecno=-10 level=4}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': True,
            'timestamp': 1234567890,
            'connection_status': 1,
            'lac': 12345,
            'cid': 67890,
            'psc': 123,
            'uarfcn': 456,
            'mcc': 310,
            'mnc': 260,
            'alpha_long': 'Verizon',
            'alpha_short': 'VZW',
            'ss': -85,
            'ber': 99,
            'rscp': -75,
            'ecno': -10,
            'level': 4
        }
        for k in expected.keys():
            self.assertIn(k, result, f"Key {k} not found in result")

        for k in expected.keys():
            self.assertEqual(result[k], expected[k], f"Value for {k} does not match expected value")
    
    def test_parse_wcdma_partial_data(self):
        """Test parsing WCDMA string with only some fields present."""
        cell_info = "mRegistered=No mMcc=310 mMnc=260 ss=-90 level=2"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'registered': False,
            'mcc': 310,
            'mnc': 260,
            'ss': -90,
            'level': 2
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_wcdma_empty_string(self):
        """Test parsing empty WCDMA string."""
        cell_info = ""
        
        result = parse_wcdma(cell_info)
        
        self.assertEqual(result, {})
    
    def test_parse_wcdma_registered_no(self):
        """Test parsing WCDMA string with registered=No."""
        cell_info = "mRegistered=No"
        
        result = parse_wcdma(cell_info)
        
        self.assertEqual(result, {'registered': False})
    
    def test_parse_wcdma_negative_values(self):
        """Test parsing WCDMA string with negative signal values."""
        cell_info = "ss=-100 rscp=-120 ecno=-15"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'ss': -100,
            'rscp': -120,
            'ecno': -15
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_wcdma_alpha_with_spaces(self):
        """Test parsing WCDMA string with alpha fields containing spaces."""
        cell_info = "{mAlphaLong=T-Mobile USA mAlphaShort=T-Mob}"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'alpha_long': 'T-Mobile USA',
            'alpha_short': 'T-Mob'
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_wcdma_invalid_numeric_values(self):
        """Test parsing WCDMA string with invalid numeric values."""
        cell_info = "mMcc=invalid mLac=12345"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'lac': 12345
        }
        
        self.assertEqual(result, expected)
    
    def test_parse_wcdma_timestamp_format(self):
        """Test parsing WCDMA string with timestamp in nanoseconds."""
        cell_info = "mTimeStamp=1609459200000000000ns"
        
        result = parse_wcdma(cell_info)
        
        expected = {
            'timestamp': 1609459200000000000
        }
        
        self.assertEqual(result, expected)


class TestLoadCsvData(unittest.TestCase):
    def test_load_csv_data_with_matching_header(self):
        content = "category,tag\nsidewalk,paved\nsidewalk,unpaved\n"
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = load_csv_data(temp_path, fieldnames=['category', 'tag'])
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], {'category': 'sidewalk', 'tag': 'paved'})
            self.assertEqual(result[1], {'category': 'sidewalk', 'tag': 'unpaved'})
        finally:
            os.remove(temp_path)

    def test_load_csv_data_without_header_preserves_first_row(self):
        content = "sidewalk,paved\nsidewalk,unpaved\n"
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as f:
            f.write(content)
            temp_path = f.name

        try:
            result = load_csv_data(temp_path, fieldnames=['category', 'tag'])
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], {'category': 'sidewalk', 'tag': 'paved'})
            self.assertEqual(result[1], {'category': 'sidewalk', 'tag': 'unpaved'})
        finally:
            os.remove(temp_path)

    def test_load_csv_data_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as f:
            temp_path = f.name

        try:
            result = load_csv_data(temp_path, fieldnames=['category', 'tag'])
            self.assertEqual(result, [])
        finally:
            os.remove(temp_path)


class TestExtractDataframeSnippet(unittest.TestCase):

    def test_extract_dataframe_snippet_string_bounds(self):
        df = pd.DataFrame({
            'Time (s)': [0.0, 1.0, 2.0, 3.0],
            'val': [10, 20, 30, 40]
        })

        result = extract_dataframe_snippet(df, '1', '2')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertListEqual(result['Time (s)'].tolist(), [1.0, 2.0])

    def test_extract_dataframe_snippet_float_bounds(self):
        df = pd.DataFrame({
            'Time (s)': [0.0, 1.5, 2.5, 4.0],
            'val': [10, 20, 30, 40]
        })

        result = extract_dataframe_snippet(df, 1.0, 3.0)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertListEqual(result['Time (s)'].tolist(), [1.5, 2.5])


class TestGenerateMetadata(unittest.TestCase):
    @patch('sideseeing_tools.metadata.cv2.VideoCapture')
    def test_includes_directory_and_subdirectory(self, video_capture):
        video_capture.return_value.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FPS: 25, cv2.CAP_PROP_FRAME_COUNT: 100,
            cv2.CAP_PROP_FRAME_WIDTH: 16, cv2.CAP_PROP_FRAME_HEIGHT: 12,
        }[prop]
        instance = SimpleNamespace(
            name='capture-001',
            video='video.mp4',
            geolocation_center=None,
            metadata={
                'directory': 'CITY',
                'subdirectory': 'ROUTE01-A',
                'time': {
                    'mediaStartDateTime': '2026-09-09T16:32:20.452Z',
                    'mediaStopDateTime': '2026-09-09T16:33:09.271Z',
                },
                'device': {},
            },
        )

        metadata = generate_metadata(iter([instance]), DATETIME_UTC_FORMAT)

        self.assertEqual(metadata.loc[0, 'directory'], 'CITY')
        self.assertEqual(metadata.loc[0, 'subdirectory'], 'ROUTE01-A')
