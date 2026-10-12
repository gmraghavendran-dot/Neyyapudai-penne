from backend.config import settings
BOOTSTRAP_SERVERS = settings.kafka_bootstrap_servers
TOPICS = {"incidents":"neyyapudaipenne.incidents", "sos":"neyyapudaipenne.sos", "locations":"neyyapudaipenne.locations"}
