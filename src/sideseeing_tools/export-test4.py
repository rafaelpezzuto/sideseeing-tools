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

        summary = self._create_summary(ds)

        output_dir = os.path.dirname(output_path) or '.'
        output_data_dir = os.path.join(output_dir, 'data')

        sections = {
            'sensor': self._process_sensors_data(ds, output_data_dir)
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
out_path = '/home/renzo/Documents/GitHub/sideseeing-tools/coisas/out/report.html'

r = Report()
r.generate_report(dir_path, out_path)