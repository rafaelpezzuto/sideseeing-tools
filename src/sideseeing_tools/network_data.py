import csv
import datetime
import re

from sideseeing_tools.constants import CELL_SNIPPET_HEADER, WIFI_SNIPPET_HEADER
from sideseeing_tools.sensor_data import to_dataframe

CELL_NUMERIC_FIELDS = (
    'timestamp',
    'connection_status',
    'lac',
    'cid',
    'psc',
    'uarfcn',
    'arfcn',
    'ci',
    'pci',
    'tac',
    'earfcn',
    'nci',
    'nrarfcn',
    'bandwidth',
    'mcc',
    'mnc',
    'ss',
    'ber',
    'rscp',
    'ecno',
    'rssi',
    'rsrp',
    'rsrq',
    'rssnr',
    'cqi',
    'ta',
    'csi_rsrp',
    'csi_rsrq',
    'csi_sinr',
    'ss_rsrp',
    'ss_rsrq',
    'ss_sinr',
    'level',
)

WCDMA_PATTERNS = {
    'registered': r'mRegistered=(\w+)',
    'timestamp': r'mTimeStamp=(\d+)[ns|]',
    'connection_status': r'mCellConnectionStatus=(\d+)',
    'lac': r'mLac=(\d+)',
    'cid': r'mCid=(\d+)',
    'psc': r'mPsc=(\d+)',
    'uarfcn': r'mUarfcn=(\d+)',
    'mcc': r'mMcc=(\d+)',
    'mnc': r'mMnc=(\d+)',
    'alpha_long': r'mAlphaLong=(.*?)(?=\s\w+=|\s*})',
    'alpha_short': r'mAlphaShort=(.*?)(?=\s\w+=|\s*})',
    'ss': r'ss=(-?\d+)',
    'ber': r'ber=(\d+)',
    'rscp': r'rscp=(-?\d+)',
    'ecno': r'ecno=(-?\d+)',
    'level': r'level=(\d+)',
}

CELL_PATTERNS = {
    **WCDMA_PATTERNS,
    'arfcn': r'mArfcn=(\d+)',
    'bsic': r'mBsic=(0x[0-9a-fA-F]+|\d+)',
    'ci': r'mCi=(\d+)',
    'pci': r'mPci=(\d+)',
    'tac': r'mTac=(\d+)',
    'earfcn': r'mEarfcn=(\d+)',
    'nci': r'mNci=(\d+)',
    'nrarfcn': r'mNrArfcn=(\d+)',
    'bands': r'mBands=\[([^\]]*)\]',
    'bandwidth': r'mBandwidth=(-?\d+)',
    'rssi': r'\brssi\s*=\s*(-?\d+)',
    'rsrp': r'\brsrp\s*=\s*(-?\d+)',
    'rsrq': r'\brsrq\s*=\s*(-?\d+)',
    'rssnr': r'\brssnr\s*=\s*(-?\d+)',
    'cqi': r'\bcqi\s*=\s*(-?\d+)',
    'ta': r'\b(?:ta|mTa)\s*=\s*(-?\d+)',
    'csi_rsrp': r'\bcsiRsrp\s*=\s*(-?\d+)',
    'csi_rsrq': r'\bcsiRsrq\s*=\s*(-?\d+)',
    'csi_sinr': r'\bcsiSinr\s*=\s*(-?\d+)',
    'ss_rsrp': r'\bssRsrp\s*=\s*(-?\d+)',
    'ss_rsrq': r'\bssRsrq\s*=\s*(-?\d+)',
    'ss_sinr': r'\bssSinr\s*=\s*(-?\d+)',
    'level': r'\blevel\s*=\s*(-?\d+)',
}


def _load_normalized_network(path, columns, datetime_format, start_time, end_time, data_type):
    with open(path) as stream:
        reader = csv.DictReader(stream)

        if not reader.fieldnames or 'Datetime UTC' not in reader.fieldnames:
            return None
        if not set(reader.fieldnames).issubset(set(columns)):
            return None

        rows = []

        for row in reader:
            timestamp = datetime.datetime.strptime(row['Datetime UTC'], datetime_format)

            if start_time is not None and timestamp < start_time:
                continue
            if end_time is not None and timestamp > end_time:
                continue

            row['Datetime UTC'] = timestamp

            if data_type == 'cell':
                for col in columns:
                    row.setdefault(col, '')

                for field in CELL_NUMERIC_FIELDS:
                    if row.get(field, '') != '':
                        row[field] = int(row[field])

                if row.get('registered', '') != '':
                    row['registered'] = row['registered'].lower() == 'true'
            else:
                row = {key: None if value == '' else value for key, value in row.items()}

            rows.append(row)

    return to_dataframe(rows, 1, datetime_format, data_type=data_type)


def _extract_fields(cell_info_str, patterns):
    result = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, cell_info_str)

        if match:
            value = match.group(1).strip()

            if key == 'registered':
                result[key] = value.lower() in ('yes', 'true')
            elif key in CELL_NUMERIC_FIELDS:
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = value
            else:
                result[key] = value

    return result


def parse_wcdma(cell_info_str):
    return _extract_fields(cell_info_str, WCDMA_PATTERNS)


def parse_cell_info(cell_info_str):
    """Parse Android CellInfo records across WCDMA (3G), LTE (4G), NR (5G), and GSM (2G)."""
    result = _extract_fields(cell_info_str, CELL_PATTERNS)

    tech_match = re.search(r'\bCellInfo([A-Za-z0-9]+)\b', cell_info_str)

    if tech_match:
        result['cell_type'] = tech_match.group(1).upper()

    return result


def process_cell_networks(path, datetime_format, start_time=None, end_time=None):
    normalized = _load_normalized_network(
        path, CELL_SNIPPET_HEADER, datetime_format, start_time, end_time, 'cell'
    )

    if normalized is not None:
        return normalized

    data = []

    with open(path) as fin:
        next(fin)

        for line in fin:
            try:
                datetime_str, cell_str = line.strip().split(',', 1)
            except ValueError as e:
                print(f"ERROR. Error splitting line: {line}: {e}")
                continue

            try:
                ts = datetime.datetime.strptime(datetime_str, datetime_format)
            except ValueError as e:
                print(f"ERROR. Error parsing datetime: {datetime_str}: {e}")
                continue

            try:
                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue
            except Exception as e:
                print(f"ERROR. Error checking time range: {e}")
                continue

            try:
                cell_data = parse_cell_info(cell_str)
            except Exception as e:
                print(f"ERROR. Error parsing cell data: {cell_str}: {e}")
                continue

            row = {
                'Datetime UTC': ts,
            }

            if not isinstance(cell_data, dict):
                print(f"ERROR. Parsed line is not a dictionary: {cell_data}")
                continue

            for key in CELL_SNIPPET_HEADER:
                if key != 'Datetime UTC':
                    row[key] = cell_data.get(key, '')

            data.append(row)

    return to_dataframe(data, 1, datetime_format, data_type='cell', create_time_column=True)


def process_wifi_networks(path, datetime_format, start_time=None, end_time=None):
    normalized = _load_normalized_network(
        path, WIFI_SNIPPET_HEADER, datetime_format, start_time, end_time, 'wifi'
    )

    if normalized is not None:
        return normalized

    data = []

    with open(path) as fin:
        next(fin)

        for line in fin:
            try:
                datetime_str, wifi_data = line.strip().split(",", 1)
            except ValueError as e:
                print(f"Error splitting line: {line.strip()}: {e}")
                continue

            try:
                ts = datetime.datetime.strptime(datetime_str, datetime_format)

                if start_time and ts < start_time:
                    continue
                if end_time and ts > end_time:
                    continue

            except ValueError as e:
                print(f"Error parsing datetime: {datetime_str}: {e}")
                continue

            ssid_match = re.search(r'SSID: "(.*?)"', wifi_data)
            bssid_match = re.search(r'BSSID: ([0-9a-f:]{17})', wifi_data)
            level_match = re.search(r'level: (-?\d+)', wifi_data)
            freq_match = re.search(r'frequency: (\d+)', wifi_data)
            standard_match = re.search(r'standard: (\w+)', wifi_data)

            row = {
                'Datetime UTC': datetime_str,
                'SSID': ssid_match.group(1) if ssid_match else None,
                'BSSID': bssid_match.group(1) if bssid_match else None,
                'level': level_match.group(1) if level_match else None,
                'frequency': freq_match.group(1) if freq_match else None,
                'standard': standard_match.group(1) if standard_match else None,
            }

            data.append(row)

    return to_dataframe(data, 1, datetime_format, data_type='wifi', create_time_column=True)
