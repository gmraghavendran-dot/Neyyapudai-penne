from data_engineering.kafka.publish import publish

def send_incident(message: dict) -> bool:
    return publish("incidents", message)
