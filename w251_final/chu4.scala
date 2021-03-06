/*
* find and download the azure-eventhubs-spark_2.11-2.1.6.jar
* place jar in same folder as this script
*
* sbt clean package
* 
* $SPARK_HOME/bin/spark-submit --jars azure-eventhubs-spark_2.11-2.1.6.jar --class AzureTestChu4 --packages org.apache.spark:spark-streaming_2.11:2.1.0 --master local[2] $(find target -iname "*.jar")
*/
import org.apache.spark.SparkContext
import org.apache.spark.streaming.{Seconds, StreamingContext}
import org.apache.spark.streaming.eventhubs.EventHubsUtils

import org.apache.spark.streaming._
import org.apache.spark.streaming.dstream._
import org.apache.spark.SparkContext._
// import org.apache.spark.SparkSession._

import org.apache.spark.SparkConf

import scala.util.parsing.json._

import com.microsoft.azure.eventhubs.EventData


object AzureTestChu4 {
	val totalRuntime_s: Integer = 15
	val batchDuration_s: Int = 30

	def process(rdd: EventData) : List[JamesData] = {
		val james1: JamesData = JamesData("binky", 1, 2)
		val james2: JamesData = JamesData("winky", 2, 3)
		val james3: JamesData = JamesData("sinky", 3, 4)
		val results: List[JamesData] = List(james1, james2, james3)
		return results
	}
	
	def main(args: Array[String]) {
		val progressDir: String = "/project"
		val policyName: String = "iothubowner"
		val policykey: String = "iwzIYZfKbhZr5G6nLy0lTxjhjkLcZLkNxuwV96rJCqU="
		val namespace: String = "iothub-ns-swm-hub-175554-8925ce81b4"
		val name: String = "swm-hub"
		val eventhubParameters: Map[String, String] = Map[String, String] ( "eventhubs.policyname" -> policyName, "eventhubs.policykey" -> policykey, "eventhubs.namespace" -> namespace, "eventhubs.name" -> name, "eventhubs.partition.count" -> "4", "eventhubs.consumergroup" -> "$Default")
		val sparkConf: SparkConf = new SparkConf().setAppName("Azure Test")
		val ssc: StreamingContext = new StreamingContext(sparkConf, Seconds(batchDuration_s))
		val inputDirectStream: DStream[EventData] = EventHubsUtils.createDirectStreams( ssc, namespace, progressDir, Map(name -> eventhubParameters) )
		// inputDirectStream.foreachRDD { rdd => rdd.foreach(println) } //prints: com.microsoft.azure.eventhubs.EventData@1752db92
		val windowedInputStream: DStream[EventData] = inputDirectStream.window(Seconds(batchDuration_s * 1))
		// windowedInputStream.foreachRDD { rdd => rdd.foreach(println) } //prints: com.microsoft.azure.eventhubs.EventData@1752db92
		
		// val output: DStream[Map[String,Object]] = windowedInputStream.flatMap(rdd => rdd.getProperties)
		// output.foreachRDD { rdd => rdd.foreach(println) } //prints: {content-type=application/opcua+uajson, source=mapping}
		
		// val output: DStream[String] = windowedInputStream.map(rdd => new String(rdd.getBody)) //no split
		// val output: DStream[String] = windowedInputStream.flatMap(rdd => new String(rdd.getBody).split(" ")) //split by space
		// val output: DStream[String] = windowedInputStream.flatMap(rdd => new String(rdd.getBody).split("\n")) //split by newline
		// val output: DStream[String] = windowedInputStream.flatMap(rdd => new String(rdd.getBody).split(",")) //split by comma
		// output.foreachRDD { rdd => rdd.foreach(println) } //prints: every RDD is a single line ???
		
		// val output: DStream[String] = windowedInputStream.map(rdd => new String(rdd.getBody).replace("\n", "")) //oddly, overwrites string???
		// val output: DStream[String] = windowedInputStream.map(rdd => new String(rdd.getBody).replace("\r\n", "!")) //overwrites all newlines AND carriage returns with "!"
		val output: DStream[String] = windowedInputStream.map(rdd => new String(rdd.getBody).replace("\r\n", ""))
		output.foreachRDD { rdd => rdd.foreach(println) }
		
		// val badJsonDStream: DStream[String] = windowedInputStream.map(rdd => new String(rdd.getBody))
		// val output: DStream[String] = badJsonDStream.reduceLeft((a,b) => println("r"))
		// output.foreachRDD { rdd => rdd.foreach(println) }
		
		// val output: DStream[JamesData] = windowedInputStream.flatMap(process)
		
		
		// output.foreachRDD( rdd => {
			// println(rdd)
		// })
	
		ssc.start()
		ssc.awaitTerminationOrTimeout(totalRuntime_s * 1000)
		ssc.stop(true, true)

		println(s"============ Exiting ================")
		System.exit(0)
	}
}


case class JamesData(k: String, v: Long, t: Long)

// case class D2OnTime(v: Long, t: Long)

/*
{
      "k": "D2OnTime",
      "v": "372",
      "t": 8501977764621
    },
*/