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

SUPPORTED_FILES = [
  'consumption.csv',
  'gps.csv',
  'metadata.json',
  'sensors.three.csv',
  'video.gif',
  'video.wav',
  'labels.txt',
  'labels.csv',
  'sensors.one.csv',
  'sensors.three.uncalibrated.csv',
  'video.mp4',
]
