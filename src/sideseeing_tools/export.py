from datetime import datetime, timedelta
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
    
    def _load_sideseeing_data(self, input_dir, generate_metadata=False):
        """
        Loads the dataset using sideseeing-tools.
        """
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"Input directory is not valid: {input_dir}")
            
        return sideseeing.SideSeeingDS(
            root_dir=input_dir, 
            generate_metadata=generate_metadata
        )
    
    def _format_duration(self, seconds: float) -> str:
        """
        Converts seconds into a human-like string (H:M:S).

        Args:
            seconds (float): The duration in seconds.

        Returns:
            str: A formatted string (e.g., "Xh Ym Zs") or "N/A".
        """
        if pd.isna(seconds):
            return "N/A"
        try:
            sec = int(seconds)
            td = timedelta(seconds=sec)
            total_horas = td.days * 24 + td.seconds // 3600
            minutos = (td.seconds // 60) % 60
            segundos = td.seconds % 60
            return f"{total_horas}h {minutos}m {segundos}s"
        except Exception:
            return f"{seconds:.0f} s"
        
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
        metadata_df = ds.metadata()
        
        if metadata_df.empty:
            print("WARNING: metadata.csv is empty or could not be found.")
            # Return an empty structure
            return {
                'total_instances': 0, 'total_duration_human': '0s', 
                'total_size_gb': 0, 'total_distance_km': 0,
                'duration_histogram_chart': {'bins': [], 'values': []},
                'geo_centers_map': [], 'sample_details': []
            }

        metadata_df.set_index('name', inplace=True, drop=False)

        # --- Global KPIs ---

        summary_data['total_instances'] = ds.size
        summary_data['total_duration_human'] = self._format_duration(metadata_df['media_total_time'].sum())
        summary_data['total_size_gb'] = utils.get_dir_size(data_dir_path)

        # --- Details per Sample and Aggregators ---

        sensor_types = set()
        for ax, sensors in ds.sensors.items():
            if sensors:
                sensor_types.update(list(sensors.keys()))
        sorted_sensor_types = sorted(list(sensor_types))
        
        geo_centers_map = [] 
        sample_details = []
        
        total_distance_km = 0.0 

        print("Processing sample details...")
        for instance in ds.iterator:
            try:
                meta = metadata_df.loc[instance.name]
            except KeyError:
                continue

            details = {}
            available_data_basic = []
            available_data_sensors = []
            
            details['name'] = instance.name
            details['device_str'] = f"{meta.get('manufacturer', '?')} {meta.get('model', '?')} (SO: {meta.get('so_version', '?')})"
            details['duration_human'] = self._format_duration(meta.get('media_total_time', 0))
            
            try:
                start_str = pd.to_datetime(meta.get('media_start_time')).strftime('%d/%m/%Y %H:%M')
                stop_str = pd.to_datetime(meta.get('media_stop_time')).strftime('%d/%m/%Y %H:%M')
                details['period_str'] = f"{start_str} até {stop_str}"
            except Exception:
                details['period_str'] = "N/A"
            
            # Calculate the distance for the current sample
            sample_dist_km = instance.calculate_sample_distance_traveled()
            details['distance_km'] = sample_dist_km
            
            # Add to the total
            total_distance_km += sample_dist_km
            
            details['video_str'] = f"{meta.get('video_frames', 0)} frames @ {meta.get('video_fps', 0):.1f}fps ({meta.get('video_resolution', 'N/A')})"
            
            # --- Central Map ---

            geo_center = instance.geolocation_center 
            if geo_center: 
                geo_centers_map.append({
                    'lat': geo_center[0], 
                    'lon': geo_center[1], 
                    'name': instance.name
                })

            # --- Sensor Availability Check ---

            if instance.geolocation_points is not None and not instance.geolocation_points.empty:
                available_data_basic.append('GPS')
            if instance.wifi_networks is not None and not instance.wifi_networks.empty:
                available_data_basic.append('Wi-Fi')

            for sensor_name in sorted_sensor_types:
                for axis in ['sensors1', 'sensors3', 'sensors6']: 
                    sensor_dict = getattr(instance, axis, {})
                    if sensor_name in sensor_dict and sensor_dict[sensor_name] is not None and not sensor_dict[sensor_name].empty:
                        available_data_sensors.append(sensor_name)
                        break 
            
            details['available_data_basic'] = available_data_basic
            details['available_data_sensors'] = available_data_sensors
            sample_details.append(details)
        
        # Add the total distance traveled
        summary_data['total_distance_km'] = total_distance_km
        summary_data['geo_centers_map'] = geo_centers_map
        summary_data['sample_details'] = sorted(sample_details, key=lambda x: x['name'])
        
        print("Summary generated successfully.")
        return summary_data
    
    def _process_sensors_data(self, ds: sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepares sensor data, saving one JSON per sample in the 'output_data_dir'.

        Args:
            ds (sideseeing.SideSeeingDS): The loaded dataset object.
            output_data_dir (str): The directory to save the JSON files.

        Returns:
            Optional[Dict[str, str]]: A dictionary where:
                - Key: sample name (instance_name)
                - Value: relative path to the JSON file (e.g., 'data/sensors_amostra_A.json')
        """
        print("Exporting sensors data to JSONs...")
        
        charts_by_instance: Dict[str, List[Dict]] = {}
        sensors_axis = {
            'sensors1': ['x'],
            'sensors3': ['x', 'y', 'z'],
            'sensors6': ['x', 'y', 'z', 'dx', 'dy', 'dz']
        }
        sensors = ds.sensors

        for axis, sensors_map in sensors.items():
            if not sensors_map:
                continue

            axis_columns = sensors_axis.get(axis)
            if not axis_columns:
                continue

            for sensor_name, instance_set in sensors_map.items():
                for instance_name in sorted(list(instance_set)):
                    instance = ds.instances[instance_name]
                    sensor_data_dict = getattr(instance, axis, {})
                    df = sensor_data_dict.get(sensor_name)

                    if df is not None and not df.empty:
                        # ID for the div that will hold the chart
                        chart_id = f"chart_{instance.name}_{sensor_name.replace(' ', '_')}"
                        
                        # Plotly format
                        traces = []
                        for col in axis_columns: 
                            traces.append({
                                'x': df['Time (s)'].tolist(),
                                'y': df[col].tolist(),
                                'mode': 'lines',
                                'name': col
                            })

                        layout = {
                            'title': f'<b>Sensor:</b> {sensor_name}',
                            'xaxis': {'title': 'Tempo (s)'},
                            'yaxis': {'title': 'Valor'},
                            'margin': {'l': 50, 'r': 50, 'b': 50, 't': 50} 
                        }
                        
                        chart_dict = {
                            'chart_id': chart_id,
                            'data': traces,
                            'layout': layout
                        }

                        if instance_name not in charts_by_instance:
                            charts_by_instance[instance_name] = []
                        
                        charts_by_instance[instance_name].append(chart_dict)

        if not charts_by_instance:
            return None

        os.makedirs(output_data_dir, exist_ok=True)
        # Maps instance_name -> "data/sensors_instance_name.json"
        instance_json_map: Dict[str, str] = {}
        
        for instance_name, charts_list in charts_by_instance.items():
            json_filename = f"sensors_{instance_name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            # Path that the HTML will use
            json_relative_path = f"data/{json_filename}" 

            with open(json_save_path, 'w', encoding='utf-8') as f:
                json.dump(charts_list, f) 
            
            instance_json_map[instance_name] = json_relative_path

        return instance_json_map    
        
    def _join_wifi_gps(self, wifi_df: pd.DataFrame, gps_df: pd.DataFrame) -> pd.DataFrame:
        """
        Joins Wi-Fi and GPS dataframes based on the nearest timestamp.

        Args:
            wifi_df (pd.DataFrame): DataFrame with Wi-Fi data.
            gps_df (pd.DataFrame): DataFrame with GPS data.

        Returns:
            pd.DataFrame: A merged DataFrame.
        """
        # 1 second tolerance (1000ms)
        GPS_WIFI_MERGE_TOLERANCE_MS = 1000 

        # performs a temporal join of wifi and gps data
        merged_df = pd.merge_asof(
            wifi_df.sort_values("unix_ms"),
            gps_df.sort_values("unix_ms"),
            on="unix_ms",
            direction="nearest",
            tolerance=GPS_WIFI_MERGE_TOLERANCE_MS  
        )
        # Remove records where corresponding GPS coordinates could not be found
        merged_df = merged_df[merged_df["latitude"].notna() & merged_df["longitude"].notna()]
        return merged_df
    
    def _aggregate_wifi_data(self, merged_df: pd.DataFrame) -> Dict:
        """
        Aggregates Wi-Fi data, calculating the average signal per SSID, 
        frequency band, and location.

        Args:
            merged_df (pd.DataFrame): The merged Wi-Fi and GPS dataframe.

        Returns:
            Dict: Aggregated data formatted for heatmap visualization.
        """
        if merged_df.empty:
            return {}

        # Ensure 'level' and 'frequency' are numeric
        merged_df['level'] = pd.to_numeric(merged_df['level'], errors='coerce')
        merged_df['frequency'] = pd.to_numeric(merged_df['frequency'], errors='coerce')

        # Determine the band (2.4GHz or 5GHz)
        merged_df['band'] = (merged_df['frequency'] // 1000).map({2: '2.4GHz', 5: '5GHz'})
        
        # Remove data that could not be processed
        merged_df.dropna(subset=['band', 'level', 'SSID', 'latitude', 'longitude'], inplace=True)
        if merged_df.empty:
            return {}
        
        # Group by SSID, band, and timestamp, and calculate the mean signal
        averaged_df = merged_df.groupby(
            ['SSID', 'band', 'unix_ms'], 
            as_index=False
        )['level'].mean()

        # Get location data for each timestamp
        location_data = merged_df.drop_duplicates(subset='unix_ms')[
            ['unix_ms', 'latitude', 'longitude']
        ]

        # Join the mean signal with the location
        final_df = pd.merge(averaged_df, location_data, on='unix_ms')

        # Format the output to a JSON : {'SSID_Name': {'2.4GHz': [[lat, lon, lvl], ...], '5GHz': [...]}}
        output_data = {}
        for (ssid, band), group in final_df.groupby(['SSID', 'band']):
            if ssid not in output_data:
                output_data[ssid] = {}
            
            # Prepare data in the format expected by Folium.HeatMap
            heat_data = group[['latitude', 'longitude', 'level']].values.tolist()
            output_data[ssid][band] = heat_data
        
        return output_data
    
    def _process_wifi_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepares Wi-Fi signal data, saving one JSON per sample in 'output_data_dir'.

        Args:
            ds (sideseeing.SideSeeingDS): The loaded dataset object.
            output_data_dir (str): The directory to save the JSON files.

        Returns:
            Optional[Dict[str, str]]: A dictionary where:
                - Key: sample name (instance_name)
                - Value: relative path to the JSON file (e.g., 'data/wifi_amostra_A.json')
        """
        print("Exporting Wi-Fi data to JSONs...")
        os.makedirs(output_data_dir, exist_ok=True)
        
        # Maps instance_name -> "data/wifi_instance_name.json"
        instance_json_map: Dict[str, str] = {}

        for sample in ds.iterator:
            df_wifi_raw = sample.wifi_networks
            df_gps_raw = sample.geolocation_points

            # Skip sample if it has no wifi or gps
            if df_wifi_raw is None or df_gps_raw is None or df_wifi_raw.empty or df_gps_raw.empty:
                continue

            # Prepare DFs for merge
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
            json_relative_path = f"data/{json_filename}" # Path that the HTML will use

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

        Args:
            ds (sideseeing.SideSeeingDS): The loaded dataset object.
            output_data_dir (str): The directory to save the JSON files.

        Returns:
            Optional[Dict[str, str]]: A dictionary where:
                - Key: sample name (instance_name)
                - Value: relative path to the JSON file (e.g., 'data/geo_amostra_A.json')
        """
        print("Exporting geospatial data to JSONs...")
        os.makedirs(output_data_dir, exist_ok=True)
        
        # Maps instance_name -> "data/geo_instance_name.json"
        instance_json_map: Dict[str, str] = {}

        for sample in ds.iterator:
            df_gps = sample.geolocation_points
            center = sample.geolocation_center

            if df_gps is None or df_gps.empty or center is None:
                continue

            # Data extraction
            try:
                # Get the list of [lat, lon] coordinates
                path_data = df_gps[['latitude', 'longitude']].values.tolist()
                
                output_data = {
                    "center": center, # Center [lat, lon] for centralization
                    "path": path_data # List of [lat, lon] points for the polyline
                }

            except Exception as e:
                print(f"Error extracting GPS data for {sample.name}: {e}")
                continue

            json_filename = f"geo_{sample.name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            json_relative_path = f"data/{json_filename}" # Path that the HTML will use

            try:
                with open(json_save_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f) 
                
                instance_json_map[sample.name] = json_relative_path
            except Exception as e:
                print(f"Error saving geospatial JSON for {sample.name}: {e}")

        return instance_json_map if instance_json_map else None

    def _copy_assets(self, output_dir: str):
        """
        Copy static assets (CSS/JS) bundled in the package to the output directory.
        """
        source_static = importlib.resources.files(self.DEFAULT_TEMPLATE_PACKAGE).joinpath("static")
        target_static = os.path.join(output_dir, "static")

        os.makedirs(output_dir, exist_ok=True)

        with importlib.resources.as_file(source_static) as src_fs_path:
            shutil.copytree(src_fs_path, target_static, dirs_exist_ok=True)

        print(f"Assets copied to: {target_static}")
   
    def generate_report(self, input_dir: str, output_dir: str, title: str = None, generate_metadata: bool = False):
        """
        Generate the HTML report from the SideSeeing dataset located in 'input_dir' and save it to 'output_dir'.
        """
        print(f"Loading directory: {input_dir}")
        ds = self._load_sideseeing_data(input_dir, generate_metadata)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Paths inside the output directory
        output_html = os.path.join(output_dir, "index.html")
        output_dir_data = os.path.join(output_dir, "data") 
        os.makedirs(output_dir_data, exist_ok=True)

        # Create summary
        summary = self._create_summary(ds, input_dir)

        # Process data sections
        sections = {
            'sensor': self._process_sensors_data(ds, output_dir_data),
            'wifi': self._process_wifi_data(ds, output_dir_data),
            'geo': self._process_geo_data(ds, output_dir_data)
            # TODO:
            #   create image processing method
            #   create cell network processing method
        }

        # Filter out None sections
        processed_sections = {key: value for key, value in sections.items() if value is not None}

        # Default title if not provided
        if not title:
            input_dir_stz = input_dir
            while input_dir_stz.endswith(os.sep):
                input_dir_stz = input_dir_stz[:-1]
            title = f"SideSeeing Report - {os.path.basename(input_dir_stz)}"

        context = {
            "title": title,
            "sections": processed_sections,
            "summary": summary, 
            "data_geracao": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }

        html_data = self.template.render(context)

        with open(output_html, 'w', encoding='utf-8') as f:
            f.write(html_data)

        self._copy_assets(output_dir)
        print(f"Report generated successfully at: {output_html}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SideSeeing HTML report from dataset directory.")

    parser.add_argument("-i", "--input_dir", help="Path to the SideSeeing dataset directory.", required=True)
    parser.add_argument("-o", "--output_dir", help="Path to save the generated HTML report.", default="output")
    parser.add_argument("-t", "--title", help="Report title.", default=None)
    parser.add_argument("-g", "--generate_metadata", help="Generate metadata.csv if not present.", action="store_true")

    args = parser.parse_args()

    r = Report()
    r.generate_report(args.input_dir, args.output_dir, args.title, args.generate_metadata)
