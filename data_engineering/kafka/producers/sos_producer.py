from data_engineering.kafka.publish import publish

def send_sos(message: dict) -> bool:
    return publish("sos", message)
