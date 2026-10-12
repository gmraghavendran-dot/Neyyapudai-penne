import logging
logger = logging.getLogger("neyyapudaipenne")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
