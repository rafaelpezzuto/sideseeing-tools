import os
import json
import pandas as pd
import numpy as np
import shutil
import importlib.resources
from . import sideseeing, utils
from datetime import datetime, timedelta
from jinja2 import Environment, PackageLoader
from typing import List, Dict, Tuple, Optional

class Report:

    DEFAULT_TEMPLATE_PACKAGE = "sideseeing_tools.templates"
    DEFAULT_TEMPLATE_NAME = "template.html"

    def __init__(self):
        """
        Inicializa a classe Report.
        """
        env = Environment(
            loader=PackageLoader(self.DEFAULT_TEMPLATE_PACKAGE.split('.')[0], 
                                 self.DEFAULT_TEMPLATE_PACKAGE.split('.', 1)[1])
        )
        env.filters['tojson'] = json.dumps
        self.template = env.get_template(self.DEFAULT_TEMPLATE_NAME)

    def _load_sideseeing_data(self, dir_path: str) -> Tuple[str, sideseeing.SideSeeingDS]:
        """
        Carrega o dataset usando o sideseeing-tools.
        """
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(f"O caminho especificado não é um diretório: {dir_path}")
            
        ds = sideseeing.SideSeeingDS(root_dir=dir_path)
        title = f"Relatório de '{os.path.basename(dir_path)}'"
        return title, ds
    
    def _format_duration(self, seconds: float) -> str:
        """
        Converte segundos em uma string human-like (H:M:S).
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
            Gera o dicionário de resumo para o template.
            """
            print("Gerando resumo do dataset...")
            summary_data = {}
            metadata_df = ds.metadata()
            
            if metadata_df.empty:
                print("AVISO: metadata.csv está vazio ou não foi encontrado.")
                # Retornamos uma estrutura vazia
                return {
                    'total_instances': 0, 'total_duration_human': '0s', 
                    'total_size_gb': 0, 'total_distance_km': 0,
                    'duration_histogram_chart': {'bins': [], 'values': []},
                    'geo_centers_map': [], 'sample_details': []
                }

            metadata_df.set_index('name', inplace=True, drop=False)

            # --- KPIs Globais ---

            summary_data['total_instances'] = ds.size
            summary_data['total_duration_human'] = self._format_duration(metadata_df['media_total_time'].sum())
            summary_data['total_size_gb'] = utils.get_dir_size(data_dir_path)

            # --- Detalhes por Amostra e Agregadores ---

            sensor_types = set()
            for ax, sensors in ds.sensors.items():
                if sensors:
                    sensor_types.update(list(sensors.keys()))
            sorted_sensor_types = sorted(list(sensor_types))
            
            geo_centers_map = [] 
            sample_details = []
            
            total_distance_km = 0.0 

            print("Processando detalhes de cada amostra...")
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
                
                # Calcula a distância da amostra atual
                sample_dist_km = instance.calculate_sample_distance_traveled()
                details['distance_km'] = sample_dist_km
                
                # Adiciona ao total
                total_distance_km += sample_dist_km
                
                details['video_str'] = f"{meta.get('video_frames', 0)} frames @ {meta.get('video_fps', 0):.1f}fps ({meta.get('video_resolution', 'N/A')})"
                
                # --- Mapa Central ---

                geo_center = instance.geolocation_center 
                if geo_center: 
                    geo_centers_map.append({
                        'lat': geo_center[0], 
                        'lon': geo_center[1], 
                        'name': instance.name
                    })

                # --- Checagem de Disponibilidade de Sensores ---

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
            
            # Adicionamos o total da distância percorrida
            summary_data['total_distance_km'] = total_distance_km
            summary_data['geo_centers_map'] = geo_centers_map
            summary_data['sample_details'] = sorted(sample_details, key=lambda x: x['name'])
            
            print("Sumário gerado com sucesso.")
            return summary_data
    
    def _process_sensors_data(self, ds: sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepara os dados dos sensores, salvando um JSON por amostra no diretório 'output_data_dir'.

        Retorna um dicionário onde:
            - Chave: nome da amostra (instance_name)
            - Valor: caminho relativo para o arquivo JSON (ex: 'data/sensors_amostra_A.json')
        """
        print("Preparando dados dos sensores (exportando para JSONs)...")
        
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
                        # ID para a div que terá o gráfico
                        chart_id = f"chart_{instance.name}_{sensor_name.replace(' ', '_')}"
                        
                        # formato Plotly
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
        # Mapeia instance_name -> "data/sensors_instance_name.json"
        instance_json_map: Dict[str, str] = {}
        
        for instance_name, charts_list in charts_by_instance.items():
            json_filename = f"sensors_{instance_name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            # Caminho que o HTML usará
            json_relative_path = f"data/{json_filename}" 

            with open(json_save_path, 'w', encoding='utf-8') as f:
                json.dump(charts_list, f) 
            
            instance_json_map[instance_name] = json_relative_path

        return instance_json_map    
        
    def _join_wifi_gps(self, wifi_df: pd.DataFrame, gps_df: pd.DataFrame) -> pd.DataFrame:
        """
        Une os dataframes de wifi e gps com base no timestamp mais próximo.
        """
        # tolerância de 1 segundo (1000ms)
        GPS_WIFI_MERGE_TOLERANCE_MS = 1000 
        
        # faz uma junção temporal dos dados de wifi e gps
        merged_df = pd.merge_asof(
            wifi_df.sort_values("unix_ms"),
            gps_df.sort_values("unix_ms"),
            on="unix_ms",
            direction="nearest",
            tolerance=GPS_WIFI_MERGE_TOLERANCE_MS  
        )
        # Removemos registros onde não foi possível encontrar coordenadas GPS correspondentes
        merged_df = merged_df[merged_df["latitude"].notna() & merged_df["longitude"].notna()]
        return merged_df
    
    def _aggregate_wifi_data(self, merged_df: pd.DataFrame) -> Dict:
        """
        Agrega os dados de wifi, calculando a média do sinal por SSID, banda de frequência e localização.
        """
        if merged_df.empty:
            return {}

        # Garante que 'level' e 'frequency' são numéricos
        merged_df['level'] = pd.to_numeric(merged_df['level'], errors='coerce')
        merged_df['frequency'] = pd.to_numeric(merged_df['frequency'], errors='coerce')

        # Determina a banda (2.4GHz ou 5GHz)
        merged_df['band'] = (merged_df['frequency'] // 1000).map({2: '2.4GHz', 5: '5GHz'})
        
        # Remove dados que não puderam ser processados
        merged_df.dropna(subset=['band', 'level', 'SSID', 'latitude', 'longitude'], inplace=True)
        if merged_df.empty:
            return {}
        
        # Agrupa por SSID, banda e timestamp, e calcula a média do sinal
        averaged_df = merged_df.groupby(
            ['SSID', 'band', 'unix_ms'], 
            as_index=False
        )['level'].mean()

        # Pega os dados de localização para cada timestamp
        location_data = merged_df.drop_duplicates(subset='unix_ms')[
            ['unix_ms', 'latitude', 'longitude']
        ]

        # Junta a média do sinal com a localização
        final_df = pd.merge(averaged_df, location_data, on='unix_ms')

        # Formata a saída para um JSON : {'SSID_Name': {'2.4GHz': [[lat, lon, lvl], ...], '5GHz': [...]}}
        output_data = {}
        for (ssid, band), group in final_df.groupby(['SSID', 'band']):
            if ssid not in output_data:
                output_data[ssid] = {}
            
            # Prepara os dados no formato esperado do Folium.HeatMap
            heat_data = group[['latitude', 'longitude', 'level']].values.tolist()
            output_data[ssid][band] = heat_data
        
        return output_data
    
    def _process_wifi_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
        """
        Prepara os dados dos sinais de Wi-Fi, salvando um JSON por amostra no diretório 'output_data_dir'.

        Retorna um dicionário onde:
            - Chave: nome da amostra (instance_name)
            - Valor: caminho relativo para o arquivo JSON (ex: 'data/wifi_amostra_A.json')
        """
        print("Preparando dados de sinais Wi-Fi (exportando para JSONs)...")
        os.makedirs(output_data_dir, exist_ok=True)
        
        # Mapeia instance_name -> "data/wifi_instance_name.json"
        instance_json_map: Dict[str, str] = {}

        for sample in ds.iterator:
            df_wifi_raw = sample.wifi_networks
            df_gps_raw = sample.geolocation_points

            # Pular amostra se não tiver wifi ou gps
            if df_wifi_raw is None or df_gps_raw is None or df_wifi_raw.empty or df_gps_raw.empty:
                continue

            # Preparar DFs para o merge
            try:
                df_wifi = df_wifi_raw[['Datetime UTC', 'SSID', 'level', 'frequency']].copy()
                df_wifi["unix_ms"] = pd.to_datetime(df_wifi["Datetime UTC"]).astype('int64') // 10**6

                df_gps = df_gps_raw[['Datetime UTC', 'latitude', 'longitude']].copy()
                df_gps["unix_ms"] = pd.to_datetime(df_gps["Datetime UTC"]).astype('int64') // 10**6
                
                df_wifi = df_wifi[["unix_ms", "SSID", "level", "frequency"]]
                df_gps = df_gps[["unix_ms", "latitude", "longitude"]]
            
            except Exception as e:
                print(f"ERRO ao preparar DFs para {sample.name}: {e}")
                continue

            merged_data = self._join_wifi_gps(df_wifi, df_gps)
            aggregated_data = self._aggregate_wifi_data(merged_data)

            if not aggregated_data:
                continue 

            json_filename = f"wifi_{sample.name}.json"
            json_save_path = os.path.join(output_data_dir, json_filename)
            json_relative_path = f"data/{json_filename}" # Caminho que o HTML usará

            try:
                with open(json_save_path, 'w', encoding='utf-8') as f:
                    json.dump(aggregated_data, f) 
                
                instance_json_map[sample.name] = json_relative_path
            except Exception as e:
                print(f"ERRO ao salvar JSON de Wi-Fi para {sample.name}: {e}")


        print(f"Dados de Wi-Fi processados para {len(instance_json_map)} amostras.")
        return instance_json_map if instance_json_map else None

    def _process_geo_data(self, ds:sideseeing.SideSeeingDS, output_data_dir: str) -> Optional[Dict[str, str]]:
            """
            Prepara os dados geoespaciais (rotas GPS), salvando um JSON por amostra no diretório 'output_data_dir'.

            Retorna um dicionário onde:
                - Chave: nome da amostra (instance_name)
                - Valor: caminho relativo para o arquivo JSON (ex: 'data/geo_amostra_A.json')
            """
            print("Preparando dados geoespaciais (exportando para JSONs)...")
            os.makedirs(output_data_dir, exist_ok=True)
            
            # Mapeia instance_name -> "data/geo_instance_name.json"
            instance_json_map: Dict[str, str] = {}

            for sample in ds.iterator:
                df_gps = sample.geolocation_points
                center = sample.geolocation_center

                if df_gps is None or df_gps.empty or center is None:
                    continue

                # Extração dos dados
                try:
                    # Obter a lista de coordenadas [lat, lon]
                    path_data = df_gps[['latitude', 'longitude']].values.tolist()
                    
                    output_data = {
                        "center": center, # Centro [lat, lon] para centralização
                        "path": path_data # Lista de pontos [lat, lon] para a polilinha
                    }

                except Exception as e:
                    print(f"ERRO ao extrair dados GPS para {sample.name}: {e}")
                    continue

                json_filename = f"geo_{sample.name}.json"
                json_save_path = os.path.join(output_data_dir, json_filename)
                json_relative_path = f"data/{json_filename}" # Caminho que o HTML usará

                try:
                    with open(json_save_path, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f) 
                    
                    instance_json_map[sample.name] = json_relative_path
                except Exception as e:
                    print(f"ERRO ao salvar JSON de GEO para {sample.name}: {e}")

            print(f"Dados GEO processados para {len(instance_json_map)} amostras.")
            return instance_json_map if instance_json_map else None

    def _copy_assets(self, output_dir: str):
        """
        Copia os assets (CSS/JS) de dentro do pacote para o diretório de saída.
        """
        print("Copiando arquivos de assets (CSS/JS)...")
        assets = ['template.js', 'template.css']
        
        try:
            for asset in assets:
                # Encontra o arquivo dentro do pacote
                traversable = importlib.resources.files(self.DEFAULT_TEMPLATE_PACKAGE).joinpath(asset)
                
                # Abre como um arquivo temporário no sistema
                with importlib.resources.as_file(traversable) as src_path:
                    destiny_path = os.path.join(output_dir, asset)
                    shutil.copy(src_path, destiny_path)
            
            print(f"Assets copiados para {output_dir}")

        except Exception as e:
            print(f"ERRO ao copiar assets: {e}. Verifique se os arquivos de template estão incluídos no pacote.")

    def generate_report(self, dir_path: str, output_path: str):
        """
        Gera um relatório HTML completo a partir de um diretório de dados.
        """
        print(f"Lendo o diretório: {dir_path}")
        title, ds = self._load_sideseeing_data(dir_path)

        summary = self._create_summary(ds, dir_path)

        output_dir = os.path.dirname(output_path) or '.'
        output_data_dir = os.path.join(output_dir, 'data')

        sections = {
            'sensor': self._process_sensors_data(ds, output_data_dir),
            'wifi': self._process_wifi_data(ds, output_data_dir),
            'geo': self._process_geo_data(ds, output_data_dir)
            # Futuramente:
            # 'images': self._process_images_data(ds, output_data_dir)
        }

        # Filtra seções para o display   
        processed_sections = {key: value for key, value in sections.items() if value is not None}

        print("Renderizando template...")

        context = {
            "title": title,
            "sections": processed_sections,
            "summary": summary, 
            "data_geracao": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }

        html_output = self.template.render(context)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        print(f"Relatório salvo com sucesso em: {output_path}")

        self._copy_assets(output_dir)