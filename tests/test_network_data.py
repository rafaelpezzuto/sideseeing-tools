from sideseeing_tools.constants import DATETIME_UTC_FORMAT
from sideseeing_tools.network_data import (
    parse_cell_info,
    process_cell_networks,
    process_wifi_networks,
)


def test_wifi_ignores_invalid_timestamp_without_discarding_valid_rows(tmp_path):
    source = tmp_path / 'wifi.csv'
    source.write_text('datetime_utc,wifi_network\n'
                      '2024-01-01T00:00:00.000Z,SSID: "first" level: -50 frequency: 2400\n'
                      'invalid,SSID: "invalid" level: -55 frequency: 2400\n'
                      '2024-01-01T00:00:01.000Z,SSID: "second" level: -60 frequency: 2400\n')

    result = process_wifi_networks(source, DATETIME_UTC_FORMAT)

    assert result['SSID'].tolist() == ['first', 'second']
    assert result['Time (s)'].tolist() == [0, 1]


def test_parse_cell_info_supports_lte_nr_gsm_and_wcdma():
    lte = (
        'CellInfoLte:{mRegistered=YES mTimeStamp=774423298838939ns mCellConnectionStatus=0 '
        'CellIdentityLte:{ mCi=12345678 mPci=321 mTac=9876 mEarfcn=1550 mBands=[3] '
        'mBandwidth=20000 mMcc=724 mMnc=10 mAlphaLong=Vivo mAlphaShort=VIVO '
        'mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthLte: rssi=-57 rsrp=-97 '
        'rsrq=-19 rssnr=-2 cqiTableIndex=2147483647 cqi=10 ta=2 level=2 '
        'parametersUseForLevel=0 android.telephony.CellConfigLte :{ isEndcAvailable = false }}'
    )
    parsed_lte = parse_cell_info(lte)
    assert parsed_lte['cell_type'] == 'LTE'
    assert parsed_lte['registered'] is True
    assert parsed_lte['ci'] == 12345678
    assert parsed_lte['pci'] == 321
    assert parsed_lte['tac'] == 9876
    assert parsed_lte['earfcn'] == 1550
    assert parsed_lte['bands'] == '3'
    assert parsed_lte['bandwidth'] == 20000
    assert parsed_lte['mcc'] == 724
    assert parsed_lte['mnc'] == 10
    assert parsed_lte['alpha_long'] == 'Vivo'
    assert parsed_lte['rssi'] == -57
    assert parsed_lte['rsrp'] == -97
    assert parsed_lte['rsrq'] == -19
    assert parsed_lte['rssnr'] == -2
    assert parsed_lte['cqi'] == 10
    assert parsed_lte['ta'] == 2
    assert parsed_lte['level'] == 2

    nr = (
        'CellInfoNr:{mRegistered=YES mTimeStamp=884423298838939ns mCellConnectionStatus=1 '
        'CellIdentityNr:{ mPci=101 mTac=12345 mNrArfcn=632628 mBands=[78] mMcc=724 mMnc=05 '
        'mNci=9876543210 mAlphaLong=Claro 5G mAlphaShort=Claro mAdditionalPlmns={}} '
        'CellSignalStrengthNr:{ csiRsrp = -90 csiRsrq = -11 csiSinr = 14 '
        'ssRsrp = -88 ssRsrq = -10 ssSinr = 16 level = 4 }}'
    )
    parsed_nr = parse_cell_info(nr)
    assert parsed_nr['cell_type'] == 'NR'
    assert parsed_nr['registered'] is True
    assert parsed_nr['pci'] == 101
    assert parsed_nr['tac'] == 12345
    assert parsed_nr['nrarfcn'] == 632628
    assert parsed_nr['nci'] == 9876543210
    assert parsed_nr['bands'] == '78'
    assert parsed_nr['csi_rsrp'] == -90
    assert parsed_nr['ss_rsrp'] == -88
    assert parsed_nr['ss_rsrq'] == -10
    assert parsed_nr['ss_sinr'] == 16
    assert parsed_nr['level'] == 4

    gsm = (
        'CellInfoGsm:{mRegistered=NO mTimeStamp=774423298838939ns mCellConnectionStatus=0 '
        'CellIdentityGsm:{ mLac=1234 mCid=56789 mArfcn=128 mBsic=0x12 mMcc=724 mMnc=10 '
        'mAlphaLong=Vivo mAlphaShort=VIVO} CellSignalStrengthGsm: rssi=-75 ber=99 mTa=1 level=3}'
    )
    parsed_gsm = parse_cell_info(gsm)
    assert parsed_gsm['cell_type'] == 'GSM'
    assert parsed_gsm['lac'] == 1234
    assert parsed_gsm['cid'] == 56789
    assert parsed_gsm['arfcn'] == 128
    assert parsed_gsm['bsic'] == '0x12'
    assert parsed_gsm['rssi'] == -75
    assert parsed_gsm['ta'] == 1
    assert parsed_gsm['level'] == 3


def test_process_cell_networks_loads_mixed_technologies_and_normalized_csv(tmp_path):
    source = tmp_path / 'cell.csv'
    source.write_text(
        'datetime_utc,cellular_network\n'
        '2026-09-09T16:32:20.413Z,CellInfoLte:{mRegistered=YES mTimeStamp=774423298838939ns mCellConnectionStatus=0 CellIdentityLte:{ mCi=[****] mPci=[****] mTac=[****] mEarfcn=[****] mBands=[3] mBandwidth=2147483647 mMcc=724 mMnc=10 mAlphaLong=Vivo mAlphaShort=VIVO mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthLte: rssi=-57 rsrp=-97 rsrq=-19 rssnr=-2 cqiTableIndex=2147483647 cqi=2147483647 ta=2147483647 level=2 parametersUseForLevel=0 android.telephony.CellConfigLte :{ isEndcAvailable = false }}\n'
        '2026-09-09T16:32:21.413Z,CellInfoWcdma:{mRegistered=NO mTimeStamp=774423298838939ns mCellConnectionStatus=0 CellIdentityWcdma:{ mLac=36211 mCid=190805339 mPsc=350 mUarfcn=4437 mMcc=724 mMnc=05 mAlphaLong=Claro BRA mAlphaShort=Claro mAdditionalPlmns={} mCsgInfo=null} CellSignalStrengthWcdma: ss=-73 ber=99 rscp=-24 ecno=0 level=4}\n'
    )

    df = process_cell_networks(source, DATETIME_UTC_FORMAT)

    assert df['cell_type'].tolist() == ['LTE', 'WCDMA']
    assert df['registered'].tolist() == [True, False]
    assert df['alpha_long'].tolist() == ['Vivo', 'Claro BRA']
    assert df['rsrp'].iloc[0] == -97
    assert df['rssi'].iloc[0] == -57
    assert df['lac'].iloc[1] == 36211
    assert df['rscp'].iloc[1] == -24

    normalized_path = tmp_path / 'cell_normalized.csv'
    df.drop(columns=['Time (s)']).assign(
        **{'Datetime UTC': ['2026-09-09T16:32:20.413Z', '2026-09-09T16:32:21.413Z']}
    ).to_csv(normalized_path, index=False)

    reloaded = process_cell_networks(normalized_path, DATETIME_UTC_FORMAT)
    assert reloaded['cell_type'].tolist() == ['LTE', 'WCDMA']
    assert reloaded['registered'].tolist() == [True, False]
    assert reloaded['rsrp'].iloc[0] == -97
    assert reloaded['lac'].iloc[1] == 36211





