from datetime import datetime, timezone


def transform_sensor_data(data):

    data["ingestion_time"] = datetime.now(timezone.utc)

    data["sampling_interval"] = 60

    # data["device_type"] = "esp32"

    # data["data_source"] = "iot_pipeline"

    return data