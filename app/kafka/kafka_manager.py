from kafka import KafkaProducer
import json
import os

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER_URL,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_event(topic: str, event: dict):
    """Отправка события в Kafka."""
    producer.send(topic, value=event)
    producer.flush()
