import json
from kafka import KafkaConsumer
from data_engineering.kafka.config.kafka_config import BOOTSTRAP_SERVERS, TOPICS


def consume():
    consumer = KafkaConsumer(
        TOPICS["incidents"], bootstrap_servers=BOOTSTRAP_SERVERS,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest", enable_auto_commit=True,
        group_id="neyyapudaipenne-api",
    )
    for message in consumer:
        yield message.value
