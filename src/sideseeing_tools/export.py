import os
import io
import base64
import json
import pandas as pd
import matplotlib.pyplot as plt
from . import sideseeing, plot
import shutil
import importlib.resources
from datetime import datetime
from jinja2 import Environment, PackageLoader
from typing import List, Dict, Tuple, Optional

class Report:

    DEFAULT_TEMPLATE_PACKAGE = "sideseeing_tools.templates"
    DEFAULT_TEMPLATE_NAME = "template_report.html"

    def __init__(self):
        """
        Inicializa a classe Report.
        """
        env = Environment(
            loader=PackageLoader(self.DEFAULT_TEMPLATE_PACKAGE.split('.')[0], 
                                 self.DEFAULT_TEMPLATE_PACKAGE.split('.', 1)[1])
        )
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

    def _create_summary(self, ds: sideseeing.SideSeeingDS) -> Dict:
        """
        Gera um dicionário com dados de resumo do dataset.
        """
        print("Gerando resumo do dataset...")
        summary_data = {}
        metadata_df = ds.metadata()

        # Extraimos as estatísticas
        if not metadata_df.empty:
            summary_data['total_instances'] = ds.size
            summary_data['total_duration_seconds'] = metadata_df['media_total_time'].sum()
            summary_data['so_versions'] = metadata_df['so_version'].unique().tolist()
            summary_data['devices_manufacturer'] = [
                f"{row['manufacturer']} {row['model']}"  for _, row in metadata_df[['manufacturer', 'model']].drop_duplicates().iterrows()
            ]
        else:
            summary_data['total_instances'] = 0
            summary_data['total_duration_seconds'] = 0
            summary_data['devices+manufacturer'] = []
            summary_data['so_versions'] = []

        # Extraimos os sensores disponiveis
        sensor_types = []
        for ax, sensors in ds.sensors.items():
            if sensors:
                sensor_types.extend(list(sensors.keys()))
        summary_data['sensor_types'] = sensor_types
        
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
        # faz uma junção temporal dos dados de wifi e gps
        merged_df = pd.merge_asof(
            wifi_df.sort_values("unix_ms"),
            gps_df.sort_values("unix_ms"),
            on="unix_ms",
            direction="nearest",
            tolerance=1000  # tolerância de 1 segundo (1000ms)
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


    def _copy_assets(self, output_dir: str):
        """
        Copia os assets (CSS/JS) de dentro do pacote para o diretório de saída.
        """
        print("Copiando arquivos de assets (CSS/JS)...")
        assets = ['template2.js', 'template.css']
        
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

        summary = self._create_summary(ds)

        output_dir = os.path.dirname(output_path) or '.'
        output_data_dir = os.path.join(output_dir, 'data')

        sections = {
            'sensor': self._process_sensors_data(ds, output_data_dir),
            'wifi': self._process_wifi_data(ds, output_data_dir)
            # Futuramente:
            # 'geo': self._process_geo_data(ds, output_data_dir),
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
        


# --- SEU SCRIPT DE TESTE ---

dir_path = '/home/renzo/Documents/GitHub/temp-SideSeeing-Exporter/dataset'
out_path = '/home/renzo/Documents/GitHub/sideseeing-tools-IC/out2/report.html'

r = Report()
r.generate_report(dir_path, out_path)

# python3 -m sideseeing_tools.export 