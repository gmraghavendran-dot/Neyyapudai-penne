from data_engineering.kafka.publish import publish

def send_location(message: dict) -> bool:
    return publish("locations", message)
