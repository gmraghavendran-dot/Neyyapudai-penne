"""Optional Spark Structured Streaming location validation bridge."""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, DoubleType, StringType

SCHEMA = StructType([
    StructField("latitude", DoubleType()), StructField("longitude", DoubleType()),
    StructField("reported_at", StringType()), StructField("source", StringType()),
])

def start(bootstrap="localhost:9092", topic="neyyapudaipenne.locations"):
    spark = SparkSession.builder.appName("NeyyapudaipenneLocationStream").getOrCreate()
    raw = spark.readStream.format("kafka").option("kafka.bootstrap.servers", bootstrap).option("subscribe", topic).option("startingOffsets", "latest").load()
    return raw.selectExpr("CAST(value AS STRING) AS json").select(from_json(col("json"), SCHEMA).alias("e")).select("e.*").filter((col("latitude").between(-90,90)) & (col("longitude").between(-180,180)))
