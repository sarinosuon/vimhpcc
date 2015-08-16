package vimhpcc

import org.hpccsystems.ws.client.platform._
import org.hpccsystems.ws.client._
import org.hpccsystems.ws.client.utils.Utils
import java.util.List
import com.hsdl.commons.FileUtils
import scala.collection.JavaConversions._

object HPCC {

    // This is meant to be invoked from the command-line from vim, display stdout results to vim console.
    // First save the complete ECL code to a temporary file
    def main(args: Array[String]) {
      if (args.length >= 3) {
        val host = args(0)
        val port = args(1).toInt
        val cluster = args(2)
        val code = FileUtils.readString(args(3))
        ecl(code, host, port, cluster)
      } else {
        System.err.println("Required: host cluster file")
      }

    }

    def ecl(code: String, host: String = "192.168.1.55", port: Int = 8010, cluster: String = "thor", jobName: String = "") {
        try {
            val platform = Platform.get("http", host, port, "hpccdemo", "hpccdemo")
            val connector = platform.getHPCCWSClient()

            val wu = new WorkunitInfo()
            wu.setMaxMonitorMillis(999999999) // no timeout
            wu.setCluster(cluster)
            wu.setJobname(jobName)

            wu.setECL(code) // the ECL to execute

            val results = connector.submitECLandGetResultsList(wu)

            var currentrs = 1
            for (each <- results) {
              Utils.print(System.out, "Resultset " + currentrs +":", false, true)
              for (item <- each)  print("[ " + item.toString() +" ]")
              currentrs += 1
              println("")
            }
        } catch  {
          case e: Exception =>
          e.printStackTrace()
        }
    }

}


