"""
Optional Spark Structured Streaming bridge.

Run only when Kafka and Spark are installed/configured. The main web
application does NOT require Spark to be running.
"""
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

SCHEMA = StructType([
    StructField("incident_type", StringType()),
    StructField("severity", StringType()),
    StructField("latitude", DoubleType()),
    StructField("longitude", DoubleType()),
    StructField("location_label", StringType()),
    StructField("description", StringType()),
    StructField("source", StringType()),
])

def start():
    spark = SparkSession.builder.appName("NeyyapudaipenneIncidentStream").getOrCreate()
    raw = (spark.readStream.format("kafka")
           .option("kafka.bootstrap.servers","localhost:9092")
           .option("subscribe","neyyapudaipenne.incidents")
           .option("startingOffsets","latest").load())
    events = (raw.selectExpr("CAST(value AS STRING) AS json")
              .select(from_json(col("json"), SCHEMA).alias("e"))
              .select("e.*")
              .filter(col("latitude").isNotNull() & col("longitude").isNotNull()))
    def sink(batch, batch_id):
        # Keep the sink deliberately small: the FastAPI service remains the
        # canonical operational writer and this bridge is an optional stream.
        records = [r.asDict() for r in batch.collect()]
        if not records:
            return
        import requests
        for record in records:
            try:
                requests.post("http://localhost:8000/api/incidents", json=record, timeout=5)
            except Exception as exc:
                print("sink error", exc)
    return events.writeStream.foreachBatch(sink).outputMode("append").start()

if __name__ == "__main__":
    query = start()
    query.awaitTermination()
