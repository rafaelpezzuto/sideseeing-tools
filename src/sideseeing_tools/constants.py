DATETIME_UTC_FORMAT ="%Y-%m-%dT%H:%M:%S.%fZ"

CONSUMPTION_FILE_FIELDNAMES = [
  'datetime_utc',
  'battery_microamperes',
]

GPS_FILE_FIELDNAMES = [
  'datetime_utc',
  'gps_interval',
  'accuracy',
  'latitude',
  'longitude',
]

LABELS_FILE_FIELDNAMES = [
  'category',
  'tag',
]

WIFI_FILE_FIELDNAMES = [
  'datetime_utc',
  'wifi_network',
]

CELL_FILE_FIELDNAMES = [
  'datetime_utc',
  'cellular_network',
] 

ONE_AXIS_SENSORS_FILE_FIELDNAMES = [
  'timestamp_nano',
  'datetime_utc',
  'name',
  'axis_x',
  'accuracy',
]

THREE_AXES_SENSORS_FILE_FIELDNAMES = [
  'timestamp_nano',
  'datetime_utc',
  'name',
  'axis_x',
  'axis_y',
  'axis_z',
  'accuracy',
]

THREE_AXES_UNCALIBRATED_SENSORS_FILE_FIELDNAMES = [
  'timestamp_nano',
  'datetime_utc',
  'name',
  'axis_x',
  'axis_y',
  'axis_z',
  'delta_x',
  'delta_y',
  'delta_z',
  'accuracy',
]

ONE_AXIS_FILE_NAME = 'sensors.one.csv'

ONE_AXIS_SNIPPET_FILE_NAME = 'sensors.one.{}_{}.csv'

THREE_AXES_FILE_NAME = 'sensors.three.csv'

THREE_AXES_SNIPPET_FILE_NAME = 'sensors.three.{}_{}.csv'

THREE_AXES_UNCALIBRATED_FILE_NAME = 'sensors.three.uncalibrated.csv'

THREE_AXES_UNCALIBRATED_SNIPPET_FILE_NAME = 'sensors.three.uncalibrated.{}_{}.csv'

GPS_FILE_NAME = 'gps.csv'

GPS_SNIPPET_FILE_NAME = 'gps.{}_{}.csv'

CONSUMPTION_FILE_NAME = 'consumption.csv'

CONSUMPTION_SNIPPET_FILE_NAME = 'consumption.{}_{}.csv'

CELL_FILE_NAME = 'cell.csv'

CELL_SNIPPET_FILE_NAME = 'cell.{}_{}.csv'

WIFI_FILE_NAME = 'wifi.csv'

WIFI_SNIPPET_FILE_NAME = 'wifi.{}_{}.csv'

VIDEO_FILE_NAME = 'video.mp4'

VIDEO_SNIPPET_FILE_NAME = 'video.{}_{}.mp4'

METADATA_FILE_NAME = 'metadata.json'

METADATA_SNIPPET_FILE_NAME = 'metadata.{}_{}.json'

SUPPORTED_FILES = [
  CONSUMPTION_FILE_NAME,
  GPS_FILE_NAME,
  CELL_FILE_NAME,
  WIFI_FILE_NAME,
  ONE_AXIS_FILE_NAME,
  THREE_AXES_FILE_NAME,
  THREE_AXES_UNCALIBRATED_FILE_NAME,
  'metadata.json',
  'video.gif',
  'video.wav',
  'labels.txt',
  'labels.csv',
  VIDEO_FILE_NAME,
]
