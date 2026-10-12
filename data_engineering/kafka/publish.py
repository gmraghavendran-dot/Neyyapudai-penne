import json
import socket
from backend.config import settings
from data_engineering.kafka.config.kafka_config import BOOTSTRAP_SERVERS, TOPICS


def is_kafka_available() -> bool:
    if not settings.enable_kafka:
        return False
    try:
        parts = BOOTSTRAP_SERVERS.split(":")
        host = parts[0] if parts[0] else "localhost"
        port = int(parts[1]) if len(parts) > 1 else 9092
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except Exception:
        return False


def publish(topic_key: str, message: dict) -> bool:
    if not is_kafka_available():
        return False
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            request_timeout_ms=1000,
        )
        producer.send(TOPICS[topic_key], message)
        producer.flush(timeout=2)
        producer.close()
        return True
    except Exception:
        return False

