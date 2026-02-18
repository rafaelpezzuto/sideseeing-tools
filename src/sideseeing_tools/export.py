from datetime import datetime
from jinja2 import Environment, PackageLoader
from typing import List, Dict, Optional

import argparse
import importlib.resources
import json
import os
import pandas as pd
import geopandas as gpd
import shutil
import re
from shapely.geometry import Point
from shapely.ops import nearest_points

from . import sideseeing, utils


class Report:

    DEFAULT_TEMPLATE_PACKAGE = "sideseeing_tools.templates"
    DEFAULT_TEMPLATE_NAME = "report.html"

    def __init__(self):
        """
        Initialize Report class.
        """
        env = Environment(
            loader=PackageLoader(self.DEFAULT_TEMPLATE_PACKAGE.split('.')[0], 
                                 self.DEFAULT_TEMPLATE_PACKAGE.split('.', 1)[1])
        )
        env.filters['tojson'] = json.dumps
        self.template = env.get_template(self.DEFAULT_TEMPLATE_NAME)
    
    def _load_sideseeing_data(self, input_dir, generate_metadata=False, google_api_key=None):
        """
        Loads the dataset using sideseeing-tools.
        """
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"Input directory is not valid: {input_dir}")
            
        return sideseeing.SideSeeingDS(
            root_dir=input_dir, 
            generate_metadata=generate_metadata,
            google_api_key=google_api_key
        )

    def _create_summary(self, ds: sideseeing.SideSeeingDS, data_dir_path: str) -> Dict:
        """
        Generates the summary dictionary for the template.

        Args:
            ds (sideseeing.SideSeeingDS): The loaded dataset object.
            data_dir_path (str): Path to the data directory (used to calculate size).

        Returns:
            Dict: A dictionary containing summary data.
        """
        print("Summarizing the dataset...")
        summary_data = {}
        metadata_df = ds.metadata(save=True)
        
        if metadata_df.empty:
            print("WARNING: metadata.csv is empty or could not be found.")
            return {
                'total_instances': 0, 'total_duration_human': '0s', 
                'total_size_gb': 0, 'total_distance_km': 0,
                'total_frames': 0, 'geo_centers_map': [], 'sample_details': []
            }

        metadata_df.set_index('name', inplace=True, drop=False)

        summary_data['total_instances'] = ds.size
        summary_data['total_duration_human'] = utils.format_duration(metadata_df['media_total_time'].sum())
        summary_data['total_size_gb'] = utils.get_dir_size(data_dir_path)
        summary_data['total_frames'] = metadata_df['video_frames'].sum()

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
            
            details = {
                'id': sample_id_counter,
                'name': instance.name
            }
            
            try:
                start_time = pd.to_datetime(meta.get('media_start_time'))
                details['collection_date'] = start_time.strftime('%Y-%m-%d')
                details['collection_datetime'] = start_time.strftime('%I:%M %p')
            except Exception:
                details['collection_date'] = "N/A"
                details['collection_datetime'] = ""
            
            details['duration'] = utils.format_duration(meta.get('media_total_time', 0))
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
                geo_centers_map.append({
                    'lat': geo_center[0],
                    'lon': geo_center[1],
                    'name': instance.name
                })

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
    
    def _get_sensor_unit(self, sensor_name: str) -> str:
        """
        Returns the unit for a given sensor name.
        """
        sensor_name_lower = sensor_name.lower()
        if 'acc' in sensor_name_lower:
            return 'm/s²'
        if 'gyr' in sensor_name_lower:
            return 'rad/s'
        if 'mag' in sensor_name_lower:
            return 'μT'
        if 'light' in sensor_name_lower or 'lux' in sensor_name_lower:
            return 'lx'
        if 'pressure' in sensor_name_lower:
            return 'hPa'
        if 'proximity' in sensor_name_lower:
            return 'cm'
        if 'humidity' in sensor_name_lower:
            return '%'
        if 'temp' in sensor_name_lower:
            return '°C'
        if 'gravity' in sensor_name_lower:
            return 'm/s²'
        return ''

    def _process_sensors_data(self, ds: sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepares sensor data, saving one JSON per sample in the 'output_data_dir'.
        """
        print("Exporting sensors data to JSONs...")

        charts_by_instance: Dict[str, List[Dict]] = {}
        sensors_axis = {
            'sensors1': ['x'],
            'sensors3': ['x', 'y', 'z'],
            'sensors6': ['x', 'y', 'z', 'dx', 'dy', 'dz']
        }

        for instance in ds.iterator:
            charts_list = []
            for axis, columns in sensors_axis.items():
                sensor_data_dict = getattr(instance, axis, {})
                for sensor_name, df in sensor_data_dict.items():
                    if df is not None and not df.empty:
                        chart_id = f"chart_{instance.name}_{sensor_name.replace(' ', '_')}"

                        traces = []
                        for col in columns:
                            traces.append({
                                'x': df['Time (s)'].tolist(),
                                'y': df[col].tolist(),
                                'mode': 'lines',
                                'name': col
                            })

                        unit = self._get_sensor_unit(sensor_name)
                        yaxis_title = f'Value ({unit})' if unit else 'Value'

                        layout = {
                            'title': f'<b>Sensor:</b> {sensor_name}',
                            'xaxis': {'title': 'Time (s)'},
                            'yaxis': {
                                'title': yaxis_title,
                                'automargin': True
                            },
                            'legend': {
                                'yanchor': "top",
                                'y': 0.99,
                                'xanchor': "left",
                                'x': 0.01
                            }
                        }

                        chart_dict = {
                            'chart_id': chart_id,
                            'data': traces,
                            'layout': layout
                        }
                        charts_list.append(chart_dict)

            if charts_list:
                charts_by_instance[instance.name] = charts_list

        if not charts_by_instance:
            return None

        os.makedirs(output_data_dir, exist_ok=True)
        instance_json_map: Dict[str, str] = {}

        for instance_name, charts_list in charts_by_instance.items():
            json_filename = f"sensors_{instance_name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            json_relative_path = f"data/{json_filename}"

            with open(json_save_path, 'w', encoding='utf-8') as f:
                json.dump(charts_list, f)

            instance_json_map[instance_name] = json_relative_path

        return instance_json_map    
        
    def _join_wifi_gps(self, wifi_df: pd.DataFrame, gps_df: pd.DataFrame, corrected_gdf: Optional[gpd.GeoDataFrame] = None) -> pd.DataFrame:
        """
        Joins Wi-Fi and GPS dataframes based on the nearest timestamp.
        If a corrected GeoDataFrame is provided, it snaps Wi-Fi points to the corrected path.
        """
        GPS_WIFI_MERGE_TOLERANCE_MS = 1000

        merged_df = pd.merge_asof(
            wifi_df.sort_values("unix_ms"),
            gps_df.sort_values("unix_ms"),
            on="unix_ms",
            direction="nearest",
            tolerance=GPS_WIFI_MERGE_TOLERANCE_MS
        )
        merged_df = merged_df[merged_df["latitude"].notna() & merged_df["longitude"].notna()]

        if corrected_gdf is not None and not corrected_gdf.empty:
            corrected_line = corrected_gdf.geometry.unary_union

            def snap_to_path(row):
                point = Point(row['longitude'], row['latitude'])
                nearest_point_on_line = nearest_points(corrected_line, point)[0]
                return pd.Series([nearest_point_on_line.y, nearest_point_on_line.x])

            merged_df[['latitude', 'longitude']] = merged_df.apply(snap_to_path, axis=1)

        return merged_df
    
    def _aggregate_wifi_data(self, merged_df: pd.DataFrame) -> Dict:
        """
        Aggregates Wi-Fi data, calculating the average signal per SSID,
        frequency band, and location.
        """
        if merged_df.empty:
            return {}

        merged_df['level'] = pd.to_numeric(merged_df['level'], errors='coerce')
        merged_df['frequency'] = pd.to_numeric(merged_df['frequency'], errors='coerce')

        merged_df['band'] = (merged_df['frequency'] // 1000).map({2: '2.4GHz', 5: '5GHz'})

        merged_df.dropna(subset=['band', 'level', 'SSID', 'latitude', 'longitude'], inplace=True)
        if merged_df.empty:
            return {}
        
        averaged_df = merged_df.groupby(
            ['SSID', 'band', 'unix_ms'],
            as_index=False
        )['level'].mean()

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
    
    def _process_wifi_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str, analysis_data: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
        """
        Prepares Wi-Fi signal data, saving one JSON per sample in 'output_data_dir'.
        """
        print("Exporting Wi-Fi data to JSONs...")
        os.makedirs(output_data_dir, exist_ok=True)

        instance_json_map: Dict[str, str] = {}
        analysis_cache = {}

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

            merged_data = self._join_wifi_gps(df_wifi, df_gps)
            aggregated_data = self._aggregate_wifi_data(merged_data)

            if not aggregated_data:
                continue

            # Add corrected path if available
            corrected_path = []
            if analysis_data and sample.name in analysis_data:
                json_path = os.path.join(os.path.dirname(output_data_dir), analysis_data[sample.name])
                if sample.name not in analysis_cache:
                    if os.path.exists(json_path):
                        with open(json_path, 'r') as f:
                            analysis_cache[sample.name] = json.load(f)

                if sample.name in analysis_cache:
                    corrected_path = analysis_cache[sample.name].get("path", [])

            output_payload = {
                "wifi_data": aggregated_data,
                "corrected_path": corrected_path,
                "path": df_gps[['latitude', 'longitude']].values.tolist()
            }

            json_filename = f"wifi_{sample.name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            json_relative_path = f"data/{json_filename}"

            try:
                with open(json_save_path, 'w', encoding='utf-8') as f:
                    json.dump(output_payload, f)

                instance_json_map[sample.name] = json_relative_path
            except Exception as e:
                print(f"Error saving Wi-Fi JSON for {sample.name}: {e}")

        return instance_json_map if instance_json_map else None

    def _process_geo_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str, analysis_data: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
        """
        Prepares geospatial data (GPS routes), saving one JSON per sample
        in the 'output_data_dir'.
        """
        print("Exporting geospatial data to JSONs...")
        os.makedirs(output_data_dir, exist_ok=True)

        instance_json_map: Dict[str, str] = {}
        analysis_cache = {}

        for sample in ds.iterator:
            df_gps = sample.geolocation_points
            center = sample.geolocation_center

            if df_gps is None or df_gps.empty or center is None:
                continue

            try:
                path_data = df_gps[['latitude', 'longitude']].values.tolist()

                output_data = {
                    "center": center,
                    "path": path_data,
                    "corrected_path": []
                }

                if analysis_data and sample.name in analysis_data:
                    json_path = os.path.join(os.path.dirname(output_data_dir), analysis_data[sample.name])

                    if sample.name not in analysis_cache:
                        if os.path.exists(json_path):
                            with open(json_path, 'r') as f:
                                analysis_cache[sample.name] = json.load(f)

                    if sample.name in analysis_cache:
                        corrected_path_data = analysis_cache[sample.name].get("path", [])
                        if corrected_path_data:
                            output_data["corrected_path"] = corrected_path_data

            except Exception as e:
                print(f"Error extracting GPS data for {sample.name}: {e}")
                continue

            json_filename = f"geo_{sample.name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            json_relative_path = f"data/{json_filename}"

            try:
                with open(json_save_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f)

                instance_json_map[sample.name] = json_relative_path
            except Exception as e:
                print(f"Error saving geospatial JSON for {sample.name}: {e}")

        return instance_json_map if instance_json_map else None

    def _get_all_frames_for_event(self, event_group: pd.DataFrame, image_dir: str, output_frames_dir: str) -> List[str]:
        """
        Gathers all frame paths for a given event group, handling multi-frame events.
        """
        frame_paths = []
        
        # Get the base timestamp and frame number pattern from the first row
        first_row = event_group.iloc[0]
        start_image_name = first_row['start_image']
        end_image_name = first_row['end_image']

        start_match = re.match(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})_(\d+)_ms\.jpg', start_image_name)
        end_match = re.match(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})_(\d+)_ms\.jpg', end_image_name)

        if not start_match or not end_match:
            return []

        frame_ts, start_frame_num_str = start_match.groups()
        _, end_frame_num_str = end_match.groups()
        
        start_frame_num = int(start_frame_num_str)
        end_frame_num = int(end_frame_num_str)

        parts = frame_ts.split('-')
        unnormalized_sample_name = f"{''.join(parts[:3])}-{''.join(parts[3:])}"

        for frame_num in range(start_frame_num, end_frame_num + 1):
            frame_image_name = f"{frame_ts}_{frame_num:05d}_ms.jpg"
            
            src_img_path = os.path.join(image_dir, unnormalized_sample_name, frame_image_name)

            if not os.path.exists(src_img_path):
                print(f"Warning: Source image not found at {src_img_path}. Skipping frame.")
                continue

            unique_img_filename = f"{unnormalized_sample_name.replace('-', '')}_{frame_image_name}"
            dest_img_path = os.path.join(output_frames_dir, unique_img_filename)

            if not os.path.exists(dest_img_path):
                shutil.copy(src_img_path, dest_img_path)

            frame_paths.append(f"frames/{unique_img_filename}")
            
        return sorted(list(set(frame_paths)))

    def _process_analysis_data(self, ds: sideseeing.SideSeeingDS, events_csv_path: str, gpkg_dir: str, image_dir: str, output_dir: str) -> Optional[Dict[str, str]]:
        """
        Integrates analysis results with geospatial data and images.
        """
        if not events_csv_path or not os.path.exists(events_csv_path):
            return None
        if not gpkg_dir or not os.path.isdir(gpkg_dir):
            return None
        if not image_dir or not os.path.isdir(image_dir):
            return None

        print("Exporting sidewalk assessment data to JSONs...")
        output_data_dir = os.path.join(output_dir, "data")
        output_frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(output_data_dir, exist_ok=True)
        os.makedirs(output_frames_dir, exist_ok=True)

        try:
            events_df = pd.read_csv(events_csv_path)
        except Exception as e:
            print(f"Error reading events CSV: {e}")
            return None

        if events_df.empty:
            print("No events found in events file.")
            return None
        
        print(f"Found {len(events_df)} events in CSV.")

        timestamp_map = {
            re.search(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})', sample.name).group(1): sample.name
            for sample in ds.iterator if re.search(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})', sample.name)
        }
        print(f"Timestamp to full name mapping: {timestamp_map}")

        points_by_sample = {}
        paths_by_sample = {}
        gpkg_cache = {}
        instance_json_map = {}

        # Group by event_id to handle multi-frame events correctly
        unique_events = events_df.drop_duplicates(subset='event_id', keep='first')

        for _, row in unique_events.iterrows():
            try:
                event_id = row['event_id']
                event_group = events_df[events_df['event_id'] == event_id]
                
                start_image = row['start_image']
                
                match = re.match(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})_(\d+)_ms\.jpg', start_image)
                if not match:
                    print(f"Warning: Could not parse image filename '{start_image}' for event '{event_id}'. Skipping.")
                    continue

                timestamp_name, _ = match.groups()
                sample_name = timestamp_map.get(timestamp_name)

                if not sample_name:
                    print(f"Warning: No matching sample for timestamp '{timestamp_name}' in event '{event_id}'. Skipping.")
                    continue

                if sample_name not in points_by_sample:
                    points_by_sample[sample_name] = []

                if sample_name not in gpkg_cache:
                    gpkg_path = os.path.join(gpkg_dir, f"{timestamp_name}.gpkg")
                    if os.path.exists(gpkg_path):
                        gdf = gpd.read_file(gpkg_path)
                        gpkg_cache[sample_name] = gdf
                        if not gdf.empty:
                            paths_by_sample[sample_name] = [[geom.y, geom.x] for geom in gdf.geometry if geom]
                    else:
                        print(f"Warning: GPKG file not found for {sample_name}, skipping route path.")
                        gpkg_cache[sample_name] = None

                frame_paths = self._get_all_frames_for_event(event_group, image_dir, output_frames_dir)
                if not frame_paths:
                    continue

                point_info = {
                    'latitude': row['center_latitude'],
                    'longitude': row['center_longitude'],
                    'type': row['feature'],
                    'frames': frame_paths,
                    'event_id': event_id,
                    'length_meters': row['length_meters']
                }
                points_by_sample[sample_name].append(point_info)

            except Exception as e:
                print(f"Error processing event group {row['event_id']}: {e}")

        print(f"Processed points by sample: { {k: len(v) for k, v in points_by_sample.items()} }")

        for sample_name, points in points_by_sample.items():
            if not points:
                continue

            center = next((s.geolocation_center for s in ds.iterator if s.name == sample_name), None)
            if not center:
                center = [points[0]['latitude'], points[0]['longitude']]

            output_data = {
                "center": center,
                "points": points,
                "path": paths_by_sample.get(sample_name, [])
            }

            json_filename = f"analysis_{sample_name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            json_relative_path = f"data/{json_filename}"

            with open(json_save_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f)

            instance_json_map[sample_name] = json_relative_path
        
        if not instance_json_map:
            print("Warning: No analysis JSON files were generated.")

        return instance_json_map if instance_json_map else None

    def generate_report(self, input_dir: str, output_dir: str, title: str = None, generate_metadata: bool = False, google_api_key: str = None, version="1", events_csv_path=None, gpkg_dir=None, image_dir=None):
        """
        Generate the HTML report from the SideSeeing dataset located in 'input_dir' and save it to 'output_dir'.
        """
        print(f"Loading directory: {input_dir}")
        ds = self._load_sideseeing_data(input_dir, generate_metadata, google_api_key)

        os.makedirs(output_dir, exist_ok=True)

        output_html = os.path.join(output_dir, "index.html")
        output_dir_data = os.path.join(output_dir, "data") 
        os.makedirs(output_dir_data, exist_ok=True)

        summary = self._create_summary(ds, input_dir)

        analysis_data = self._process_analysis_data(ds, events_csv_path, gpkg_dir, image_dir, output_dir)

        sections = {
            'sensor': self._process_sensors_data(ds, output_dir_data),
            'wifi': self._process_wifi_data(ds, output_dir_data, analysis_data),
            'geo': self._process_geo_data(ds, output_dir_data, analysis_data),
            'analysis': analysis_data
        }

        processed_sections = {key: value for key, value in sections.items() if value is not None}

        if not title:
            input_dir_stz = input_dir
            while input_dir_stz.endswith(os.sep):
                input_dir_stz = input_dir_stz[:-1]
            title = f"SideSeeing Report - {os.path.basename(input_dir_stz)}"

        context = {
            "title": title,
            "sections": processed_sections,
            "summary": summary,
            "generation_date": datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            "version": version,
        }

        html_data = self.template.render(context)

        with open(output_html, 'w', encoding='utf-8') as f:
            f.write(html_data)

        print(f"Report generated successfully at: {output_html}")

        self._copy_static_assets(output_dir)

    def _copy_static_assets(self, output_dir: str):
        """Copy the template's static assets next to the generated report."""
        destination = os.path.join(output_dir, "static")

        def _copy_from_path(static_path: str):
            if not os.path.isdir(static_path):
                print("No static assets directory found; skipping copy.")
                return

            if os.path.exists(destination):
                shutil.rmtree(destination)

            try:
                shutil.copytree(static_path, destination)
                print(f"Static assets copied to: {destination}")
            except Exception as exc:
                print(f"Failed to copy static assets: {exc}")

        try:
            static_resources = importlib.resources.files(self.DEFAULT_TEMPLATE_PACKAGE) / "static"
            with importlib.resources.as_file(static_resources) as static_path:
                _copy_from_path(str(static_path))
        except AttributeError:
            with importlib.resources.path(self.DEFAULT_TEMPLATE_PACKAGE, "static") as static_path:
                _copy_from_path(str(static_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SideSeeing HTML report from dataset directory.")

    parser.add_argument("-i", "--input_dir", help="Path to the SideSeeing dataset directory.", required=True)
    parser.add_argument("-o", "--output_dir", help="Path to save the generated HTML report.", default="output")
    parser.add_argument("-t", "--title", help="Report title.", default=None)
    parser.add_argument("-v", "--version", help="Version number", default="1")
    parser.add_argument("-g", "--generate_metadata", help="Generate metadata.csv if not present.", action="store_true")
    parser.add_argument("-k", "--google_api_key", help="Google API key")
    parser.add_argument("--events-csv", help="Path to the events CSV file (e.g., map_events.csv).")
    parser.add_argument("--gpkg-dir", help="Path to the directory with GPKG files.")
    parser.add_argument("--image-dir", help="Path to the base directory for image sequences (e.g., 01_image_sequences).")

    args = parser.parse_args()

    r = Report()
    r.generate_report(
        args.input_dir,
        args.output_dir,
        args.title,
        args.generate_metadata,
        args.google_api_key,
        args.version,
        args.events_csv,
        args.gpkg_dir,
        args.image_dir
    )
