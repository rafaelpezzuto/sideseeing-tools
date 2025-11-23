from datetime import datetime
from jinja2 import Environment, PackageLoader
from typing import List, Dict, Optional

import argparse
import importlib.resources
import json
import os
import pandas as pd
import shutil

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
                'geo_centers_map': [], 'sample_details': []
            }

        metadata_df.set_index('name', inplace=True, drop=False)

        summary_data['total_instances'] = ds.size
        summary_data['total_duration_human'] = utils.format_duration(metadata_df['media_total_time'].sum())
        summary_data['total_size_gb'] = utils.get_dir_size(data_dir_path)

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
        
    def _join_wifi_gps(self, wifi_df: pd.DataFrame, gps_df: pd.DataFrame) -> pd.DataFrame:
        """
        Joins Wi-Fi and GPS dataframes based on the nearest timestamp.
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
    
    def _process_wifi_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepares Wi-Fi signal data, saving one JSON per sample in 'output_data_dir'.
        """
        print("Exporting Wi-Fi data to JSONs...")
        os.makedirs(output_data_dir, exist_ok=True)
        
        instance_json_map: Dict[str, str] = {}

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

    def _process_geo_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepares geospatial data (GPS routes), saving one JSON per sample 
        in the 'output_data_dir'.
        """
        print("Exporting geospatial data to JSONs...")
        os.makedirs(output_data_dir, exist_ok=True)
        
        instance_json_map: Dict[str, str] = {}

        for sample in ds.iterator:
            df_gps = sample.geolocation_points
            center = sample.geolocation_center

            if df_gps is None or df_gps.empty or center is None:
                continue

            try:
                path_data = df_gps[['latitude', 'longitude']].values.tolist()
                
                output_data = {
                    "center": center,
                    "path": path_data
                }

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

    def generate_report(self, input_dir: str, output_dir: str, title: str = None, generate_metadata: bool = False, google_api_key: str = None, version="1"):
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

        sections = {
            'sensor': self._process_sensors_data(ds, output_dir_data),
            'wifi': self._process_wifi_data(ds, output_dir_data),
            'geo': self._process_geo_data(ds, output_dir_data)
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

    args = parser.parse_args()

    r = Report()
    r.generate_report(args.input_dir, args.output_dir, args.title, args.generate_metadata, args.google_api_key, args.version)
