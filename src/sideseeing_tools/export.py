import os
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
import sideseeing, plot
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, Template
from typing import List, Dict, Tuple, Optional

class Report:

    DEFAULT_TEMPLATE = "/home/renzo/Documents/GitHub/temp-SideSeeing-Exporter/templates/t2.html"

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

    def _process_sensors_data(self, ds: sideseeing.SideSeeingDS) -> Optional[str]:
        """
        Processa os dados de sensores usando a função externa plot_sensor para cada instância.
        """
        print("Processando dados de sensores...")
        html_components = []
        plotter = plot.SideSeeingPlotter(ds)
        sensors_axis = {
            'sensors1': ['x'],
            'sensors3': ['x', 'y', 'z'],
            'sensors6': ['x', 'y', 'z', 'dx', 'dy', 'dz']
        }
        sensors = ds.sensors

        for axis, sensors in sensors.items():
            if not sensors:
                continue

            axis_columns = sensors_axis.get(axis)
            if not axis_columns:
                continue

            for sensor, instance_set in sensors.items():
                # Cabeçalho para o tipo de sensor
                html_components.append(f"<hr><h3>Sensor: {sensor}</h3>")
                
                # Iteramos sobre cada instância
                for instance_name in sorted(list(instance_set)):
                    instance = ds.instances[instance_name]
                    sensor_data_dict = getattr(instance, axis, {})
                    df = sensor_data_dict.get(sensor)

                    if df is not None and not df.empty:
                        fig, _ = plotter.plot_sensor(data=df, time_column='Time (s)', axis_columns=axis_columns, title=f"Amostra: {instance.name}")

                        # Processa a figura retornada para embutir no HTML
                        if fig:
                            buf = io.BytesIO()
                            fig.savefig(buf, format='png', bbox_inches='tight')
                            plt.close(fig)
                            img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                            html_components.append(f'<img src="data:image/png;base64,{img_base64}" class="img-fluid mb-4"/>')

        if not html_components:
            return "<p>Nenhum dado de sensor processável foi encontrado no dataset.</p>"

        return "\n".join(html_components)
    
    # separar os sensores

    def generate_report(self, dir_path: str, output_path: str, template_path: Optional[str] = None):
        """
        Gera um relatório HTML completo a partir de um diretório de dados.
        """
        print(f"Lendo o diretório: {dir_path}")
        title, ds = self._load_sideseeing_data(dir_path)

        summary = self._create_summary(ds)

        # Processa as diferentes seções do relatório
        sections = {
            'sensor': self._process_sensors_data(ds)
            # Futuramente:
            # 'geo': self._process_geo_data(ds),
            # 'images': self._process_images_data(ds)
        }
        
        # Filtra seções que não foram processadas
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
out_path = '/home/renzo/Documents/GitHub/temp-SideSeeing-Exporter/out/1.html'
r = Report()
r.generate_report(dir_path, out_path)
