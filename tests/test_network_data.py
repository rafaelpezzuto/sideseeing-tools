from sideseeing_tools.constants import DATETIME_UTC_FORMAT
from sideseeing_tools.network_data import process_wifi_networks


def test_wifi_ignores_invalid_timestamp_without_discarding_valid_rows(tmp_path):
    source = tmp_path / 'wifi.csv'
    source.write_text('datetime_utc,wifi_network\n'
                      '2024-01-01T00:00:00.000Z,SSID: "first" level: -50 frequency: 2400\n'
                      'invalid,SSID: "invalid" level: -55 frequency: 2400\n'
                      '2024-01-01T00:00:01.000Z,SSID: "second" level: -60 frequency: 2400\n')

    result = process_wifi_networks(source, DATETIME_UTC_FORMAT)

    assert result['SSID'].tolist() == ['first', 'second']
    assert result['Time (s)'].tolist() == [0, 1]
