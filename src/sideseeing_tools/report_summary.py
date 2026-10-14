import os

import numpy as np
import pandas as pd

from sideseeing_tools import constants, metadata, formatting, file_stats


def create_summary(ds, data_dir_path, google_api_key=None):
    """Build dataset totals and per-recording report details."""
    print("Summarizing the dataset...")
    summary_data = {}
    metadata_df = metadata.generate_metadata(
        ds.iterator, constants.DATETIME_UTC_FORMAT, google_api_key
    )

    if metadata_df.empty:
        print("WARNING: Dataset has no recordings.")

        return {
            'total_instances': 0,
            'total_duration_human': '0s',
            'total_size_gb': 0,
            'total_distance_km': 0,
            'geo_centers_map': [],
            'sample_details': [],
        }

    metadata_df.set_index('name', inplace=True, drop=False)

    summary_data['total_instances'] = ds.size

    if 'media_type' in metadata_df:
        durations = pd.to_numeric(metadata_df['media_total_time'], errors='raise')
    else:
        fps = pd.to_numeric(metadata_df['video_fps'], errors='raise')
        frames = pd.to_numeric(metadata_df['video_frames'], errors='raise')

        if not np.isfinite(fps).all() or (fps <= 0).any():
            raise ValueError('Cannot calculate duration from invalid video metadata')

        durations = frames / fps
    if not np.isfinite(durations).all() or (durations <= 0).any():
        raise ValueError('Cannot calculate duration from invalid media metadata')

    metadata_df['available_media_duration_s'] = durations
    summary_data['total_duration_human'] = formatting.format_duration(durations.sum())
    size_path = ds.data_dir if os.path.isfile(data_dir_path) else data_dir_path
    summary_data['total_size_gb'] = file_stats.get_dir_size(size_path)

    geo_centers_map = []
    sample_details = []
    total_distance_km = 0.0
    sample_id_counter = 1

    print("Processing sample details...")

    for instance in ds.iterator:
        if instance.name not in metadata_df.index:
            print(f"WARNING: Skipping sample '{instance.name}' as it's not in metadata.csv.")
            continue

        meta = metadata_df.loc[instance.name]

        details = {'id': sample_id_counter, 'name': instance.name}

        try:
            start_time = pd.to_datetime(meta.get('media_start_time'))
            details['collection_date'] = start_time.strftime('%Y-%m-%d')
            details['collection_datetime'] = start_time.strftime('%I:%M %p')
        except Exception:
            details['collection_date'] = "N/A"
            details['collection_datetime'] = ""

        details['duration'] = formatting.format_duration(meta['available_media_duration_s'])
        details['device_manufacturer'] = meta.get('manufacturer', 'N/A')
        details['device_model'] = meta.get('model', '')

        sample_dist_km = instance.calculate_sample_distance_traveled()
        details['distance_km'] = sample_dist_km
        total_distance_km += sample_dist_km

        details['video_frames'] = f"{meta.get('video_frames', 0)}"
        details['video_fps'] = f"{meta.get('video_fps', 0):.1f}"
        details['video_resolution'] = meta.get('video_resolution', 'N/A')

        details['location'] = meta.get('location', 'N/A')

        geo_center = instance.geolocation_center

        if geo_center:
            geo_centers_map.append(
                {'lat': geo_center[0], 'lon': geo_center[1], 'name': instance.name}
            )

        available_sensors_count = 0

        for axis in ['sensors1', 'sensors3', 'sensors6']:
            sensor_dict = getattr(instance, axis, {})

            if sensor_dict:
                available_sensors_count += len(sensor_dict)

        details['sensors'] = available_sensors_count
        sample_details.append(details)
        sample_id_counter += 1

    summary_data['total_distance_km'] = total_distance_km
    summary_data['geo_centers_map'] = geo_centers_map
    summary_data['sample_details'] = sorted(sample_details, key=lambda x: x['name'])

    print("Summary generated successfully.")

    return summary_data
