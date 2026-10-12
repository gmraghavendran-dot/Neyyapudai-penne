"""Optional Spark Structured Streaming SOS enrichment bridge."""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, lower, concat_ws
from pyspark.sql.types import StructType, StructField, DoubleType, StringType

SCHEMA = StructType([
    StructField("latitude", DoubleType()), StructField("longitude", DoubleType()),
    StructField("location_label", StringType()), StructField("description", StringType()),
    StructField("device_ref", StringType()),
])

def start(bootstrap="localhost:9092", topic="neyyapudaipenne.sos"):
    spark = SparkSession.builder.appName("NeyyapudaipenneSOSStream").getOrCreate()
    raw = spark.readStream.format("kafka").option("kafka.bootstrap.servers", bootstrap).option("subscribe", topic).option("startingOffsets", "latest").load()
    events = raw.selectExpr("CAST(value AS STRING) AS json").select(from_json(col("json"), SCHEMA).alias("e")).select("e.*")
    return events.filter((col("latitude").between(-90,90)) & (col("longitude").between(-180,180)))
