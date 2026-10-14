import json
import os


def _get_sensor_unit(sensor_name):
    """Returns the unit for a given sensor name."""
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


def process_sensors_data(ds, output_data_dir):
    """Prepares sensor data, saving one JSON per sample in the 'output_data_dir'."""
    print("Exporting sensors data to JSONs...")

    charts_by_instance = {}
    sensors_axis = {
        'sensors1': ['x'],
        'sensors3': ['x', 'y', 'z'],
        'sensors6': ['x', 'y', 'z', 'dx', 'dy', 'dz'],
    }

    for instance in ds.iterator:
        charts_list = []

        for axis, columns in sensors_axis.items():
            sensor_data_dict = getattr(instance, axis, None) or {}

            for sensor_name, df in sensor_data_dict.items():
                if df is not None and not df.empty:
                    chart_id = f"chart_{instance.name}_{sensor_name.replace(' ', '_')}"

                    traces = []

                    for col in columns:
                        traces.append(
                            {
                                'x': df['Time (s)'].tolist(),
                                'y': df[col].tolist(),
                                'mode': 'lines',
                                'name': col,
                            }
                        )

                    unit = _get_sensor_unit(sensor_name)
                    yaxis_title = f'Value ({unit})' if unit else 'Value'

                    layout = {
                        'title': f'<b>Sensor:</b> {sensor_name}',
                        'xaxis': {'title': 'Time (s)'},
                        'yaxis': {'title': yaxis_title, 'automargin': True},
                        'legend': {'yanchor': "top", 'y': 0.99, 'xanchor': "left", 'x': 0.01},
                    }

                    chart_dict = {'chart_id': chart_id, 'data': traces, 'layout': layout}
                    charts_list.append(chart_dict)

        if charts_list:
            charts_by_instance[instance.name] = charts_list

    if not charts_by_instance:
        return None

    os.makedirs(output_data_dir, exist_ok=True)
    instance_json_map = {}

    for instance_name, charts_list in charts_by_instance.items():
        json_filename = f"sensors_{instance_name}.json"
        json_save_path = os.path.join(output_data_dir, json_filename)
        json_relative_path = f"data/{json_filename}"

        with open(json_save_path, 'w', encoding='utf-8') as f:
            json.dump(charts_list, f)

        instance_json_map[instance_name] = json_relative_path

    return instance_json_map
