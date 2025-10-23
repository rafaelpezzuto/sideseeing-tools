import os
import io
import base64
import json
import pandas as pd
import matplotlib.pyplot as plt
import sideseeing, plot
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Dict, Tuple, Optional

class Report:

    DEFAULT_TEMPLATE = "/home/renzo/Documents/GitHub/sideseeing-tools/src/sideseeing_tools/templates/template_report.html"

    def __init__(self, default_template_path: str = DEFAULT_TEMPLATE):
        """
        Inicializa o Report com um template padrão.
        """
        self.default_template_path = default_template_path
        self._validate_template_exists(default_template_path)

    def _validate_template_exists(self, template_path: str) -> None:
        """
        Verifica se o template existe.
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"O Template {template_path} não foi encontrado.")

    def _load_template(self, template_path: Optional[str] = None) -> Template:
        """
        Carrega um template padrão ou um personalizado.
        """
        path = template_path or self.default_template_path
        self._validate_template_exists(path)
        
        template_dir = os.path.dirname(path) or '.'
        template_file_name = os.path.basename(path)
        
        env = Environment(loader=FileSystemLoader(template_dir))
        return env.get_template(template_file_name)

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

    def _process_sensors_data(self, ds: sideseeing.SideSeeingDS) -> Optional[Dict[str, List[Dict]]]:
        """
            Prepara os dados dos sensores para visualização com Plotly.js, agrupando por amostra.
            
            Retorna um dicionário onde:
            - Chave: nome da amostra (instance_name)
            - Valor: lista de dicionários com configurações para gerar gráficos, contendo:
                * chart_id: ID único para o elemento HTML do gráfico
                * data_json: dados das séries em formato JSON
                * layout_json: configurações de layout em formato JSON
            
            Returns:
                Dict[str, List[Dict]] ou None se não houver dados de sensores
        """
        print("Preparando dados dos sensores...")
        
        charts_data_grouped: Dict[str, List[Dict]] = {}
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
                    # Ordenamos as instâncias e obtemos o dicionário de dados do sensor usando getattr
                    # Depois, extraímos o DataFrame específico do sensor
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
                            'data_json': json.dumps(traces),
                            'layout_json': json.dumps(layout)
                        }

                        # Se a amostra (instance_name) ainda não está no dicionário, crie uma lista vazia
                        if instance_name not in charts_data_grouped:
                            charts_data_grouped[instance_name] = []
                        
                        charts_data_grouped[instance_name].append(chart_dict)

        if not charts_data_grouped:
            return None

        return charts_data_grouped    
    
    def generate_report(self, dir_path: str, output_path: str, template_path: Optional[str] = None):
        """
        Gera um relatório HTML completo a partir de um diretório de dados.
        """
        print(f"Lendo o diretório: {dir_path}")
        title, ds = self._load_sideseeing_data(dir_path)

        summary = self._create_summary(ds)

        sections = {
            'sensor': self._process_sensors_data(ds)
            # Futuramente:
            # 'geo': self._process_geo_data(ds),
            # 'images': self._process_images_data(ds)
        }
        
        # Filtra seções para o display
        processed_sections = {key: value for key, value in sections.items() if value is not None}

        print("Carregando template...")
        template = self._load_template(template_path)

        context = {
            "title": title,
            "sections": processed_sections,
            "summary": summary, 
            "data_geracao": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }

        html_output = template.render(context)

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        print(f"Relatório salvo com sucesso em: {output_path}")



dir_path = '/home/renzo/Documents/GitHub/temp-SideSeeing-Exporter/dataset'
out_path = '/home/renzo/Documents/GitHub/temp-SideSeeing-Exporter/out/report.html'
r = Report()
r.generate_report(dir_path, out_path)