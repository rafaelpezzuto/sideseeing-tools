import json
import os

import pandas as pd

GPS_WIFI_MERGE_TOLERANCE_MS = 1000


def _join_wifi_gps(wifi_df, gps_df):
    """Joins Wi-Fi and GPS dataframes based on the nearest timestamp."""

    merged_df = pd.merge_asof(
        wifi_df.sort_values("unix_ms"),
        gps_df.sort_values("unix_ms"),
        on="unix_ms",
        direction="nearest",
        tolerance=GPS_WIFI_MERGE_TOLERANCE_MS,
    )
    merged_df = merged_df[merged_df["latitude"].notna() & merged_df["longitude"].notna()]

    return merged_df


def _aggregate_wifi_data(merged_df):
    """Aggregates Wi-Fi data, calculating the average signal per SSID,"""
    if merged_df.empty:
        return {}

    merged_df['level'] = pd.to_numeric(merged_df['level'], errors='coerce')
    merged_df['frequency'] = pd.to_numeric(merged_df['frequency'], errors='coerce')

    merged_df['band'] = (merged_df['frequency'] // 1000).map({2: '2.4GHz', 5: '5GHz'})

    merged_df.dropna(subset=['band', 'level', 'SSID', 'latitude', 'longitude'], inplace=True)

    if merged_df.empty:
        return {}

    averaged_df = merged_df.groupby(['SSID', 'band', 'unix_ms'], as_index=False)['level'].mean()

    location_data = merged_df.drop_duplicates(subset='unix_ms')[
        ['unix_ms', 'latitude', 'longitude']
    ]

    final_df = pd.merge(averaged_df, location_data, on='unix_ms')

    output_data = {}

    for (ssid, band), group in final_df.groupby(['SSID', 'band']):
        if ssid not in output_data:
            output_data[ssid] = {}

        heat_data = group[['latitude', 'longitude', 'level']].values.tolist()
        output_data[ssid][band] = heat_data

    return output_data


def process_wifi_data(ds, output_data_dir):
    """Prepares Wi-Fi signal data, saving one JSON per sample in 'output_data_dir'."""
    print("Exporting Wi-Fi data to JSONs...")
    os.makedirs(output_data_dir, exist_ok=True)

    instance_json_map = {}

    for sample in ds.iterator:
        df_wifi_raw = sample.wifi_networks
        df_gps_raw = sample.geolocation_points

        if df_wifi_raw is None or df_gps_raw is None or df_wifi_raw.empty or df_gps_raw.empty:
            continue

        try:
            df_wifi = df_wifi_raw[['Datetime UTC', 'SSID', 'level', 'frequency']].copy()
            df_wifi["unix_ms"] = pd.to_datetime(df_wifi["Datetime UTC"]).astype('int64') // 10**6

            df_gps = df_gps_raw[['Datetime UTC', 'latitude', 'longitude']].copy()
            df_gps["unix_ms"] = pd.to_datetime(df_gps["Datetime UTC"]).astype('int64') // 10**6

            df_wifi = df_wifi[["unix_ms", "SSID", "level", "frequency"]]
            df_gps = df_gps[["unix_ms", "latitude", "longitude"]]

        except Exception as e:
            print(f"Error when preparing DFs for {sample.name}: {e}")
            continue

        merged_data = _join_wifi_gps(df_wifi, df_gps)
        aggregated_data = _aggregate_wifi_data(merged_data)

        if not aggregated_data:
            continue

        json_filename = f"wifi_{sample.name}.json"
        json_save_path = os.path.join(output_data_dir, json_filename)
        json_relative_path = f"data/{json_filename}"

        try:
            with open(json_save_path, 'w', encoding='utf-8') as f:
                json.dump(aggregated_data, f)

            instance_json_map[sample.name] = json_relative_path
        except Exception as e:
            print(f"Error saving Wi-Fi JSON for {sample.name}: {e}")

    return instance_json_map if instance_json_map else None
