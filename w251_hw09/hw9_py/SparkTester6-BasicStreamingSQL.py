from pyspark import SparkContext
from pyspark.streaming import StreamingContext
import json

'''
Test for Spark Stream to be used with a Tweet Tester, to see if we can using SQL to parse the tweets from the twitter stream
Consumes the tweets sampled by the Tweet Tester app.

On Terminal 1 run,
$ nc -lk 5555

then start typing into terminal 1, hit enter to send a line of text

On Terminal 2 run,
$ SparkTester6-BasicStreamingSQL.py

as the tweet tester streams tweets into the spark streaming app, we should see some counts

========= 2017-11-25 14:13:00 =========
+---------+-----+
|     word|total|
+---------+-----+
|      but|    1|
|following|    1|
|      the|    1|
|    never|    1|
|       do|    3|
|     that|    1|
|     this|    1|
+---------+-----+


See 
* https://spark.apache.org/docs/latest/streaming-programming-guide.html
* https://github.com/apache/spark/blob/v2.2.0/examples/src/main/python/streaming/sql_network_wordcount.py
'''

my_port = 5555
my_host = "spark-2-1"
my_batch_interval = 1 #batch interval of seconds
my_app_name = "NetworkWordCount"
my_spark_master = "local[2]" #local StreamingContext with two working threads


import sys

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import Row, SparkSession


def getSparkSessionInstance(sparkConf):
    if ('sparkSessionSingletonInstance' not in globals()):
        globals()['sparkSessionSingletonInstance'] = SparkSession\
            .builder\
            .config(conf=sparkConf)\
            .getOrCreate()
    return globals()['sparkSessionSingletonInstance']


if __name__ == "__main__":
    host, port = my_host, my_port
    sc = SparkContext(appName="PythonSqlNetworkWordCount")
    ssc = StreamingContext(sc, my_batch_interval)

    # Create a socket stream on target ip:port and count the
    # words in input stream of \n delimited text (eg. generated by 'nc')
    lines = ssc.socketTextStream(host, int(port))
    words = lines.flatMap(lambda line: line.split(" "))

    # Convert RDDs of the words DStream to DataFrame and run SQL query
    def process(time, rdd):
        print("========= %s =========" % str(time))

        try:
            # Get the singleton instance of SparkSession
            spark = getSparkSessionInstance(rdd.context.getConf())

            # Convert RDD[String] to RDD[Row] to DataFrame
            rowRdd = rdd.map(lambda w: Row(word=w))
            wordsDataFrame = spark.createDataFrame(rowRdd)

            # Creates a temporary view using the DataFrame.
            wordsDataFrame.createOrReplaceTempView("words")

            # Do word count on table using SQL and print it
            wordCountsDataFrame = \
                spark.sql("select word, count(*) as total from words group by word")
            wordCountsDataFrame.show()
        except:
            pass

    words.foreachRDD(process)
    ssc.start()
    ssc.awaitTermination()