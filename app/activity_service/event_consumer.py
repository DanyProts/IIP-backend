from kafka import KafkaConsumer
import json
import threading
import os

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")
TOPIC = "user_registered"

def process_event(event: dict):
    """Обработка события регистрации пользователя."""
    print(f"[Kafka] Получено событие: {event}")
    # Здесь можно сохранить активность в БД, отправить приветственное письмо и т.п.

def start_consumer():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BROKER_URL,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='activity-consumer-group',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    print(f"[Kafka] Слушаем события из темы '{TOPIC}'")

    for message in consumer:
        process_event(message.value)

def run_consumer_in_thread():
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
