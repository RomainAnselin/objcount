# Introduction

The `objcount.py` is a program written to review a number of statistics for specific queries in Cassandra.
It attempts to test specific use cases which can be problematic in Cassandra 4.x and requiring tweaking

# Install
After cloning the repository, run
`$ pip install -r requirements.txt`

# Usage
It is mandatory to define the `dcname` in the `conf_dummy.ini` at minimum using one of the datacenter name of the Cassandra cluster.

Example use:
```
$ python3 ./objcount.py -c conf_dummy.ini -i 10.1.2.3 -k test
```

Full usage info:
```
$ python3 objcount.py -h
usage: objcount.py [-h] -c CONF -i HOST -k KEYSPACE [-t TABLE] [-f FETCH] [-d DEBUG]

Statistics script

optional arguments:
  -h, --help            show this help message and exit
  -c CONF, --conf CONF  Configuration file to connect
  -i HOST, --host HOST  IP address for Cassandra
  -k KEYSPACE, --keyspace KEYSPACE
                        Keyspace to query
  -t TABLE, --table TABLE
                        Table to query - defaults to count_perf
  -f FETCH, --fetch FETCH
                        fetch size
  -d DEBUG, --debug DEBUG
                        debug file
```

Note: the conf file contains a number of elements that can be set for authentication (username/password) and 1-way SSL (Provide path to the Root Certificate Authority public certificate) to connect to Cassandra

# Information

## Scenario 1. Unbound queries

In case of a select without a where clause, DSE and Cassandra will run a "range" query which is a scatter and gather data accross the cluster

Cassandra 4 implements a guardrail on queries that would bring back more than 128Mb of data to the coordinator in one page.

`objcount.py` will iterate through the results and provide number of rows retrieved by the driver, along average/min/max size of the blobs.
The size of the query is estimated at `avg_blob_size * number_of_rows`

For example, if there are just under 5000 rows, and the average size of the blob is 200kb, that means the query would bring back ~1GB of data **in one page** to the driver.

 :warning: Note: this implies the "major" part of the query size is due to the column analyzed for statistics. If multiple columns make for the larger data set, this program is void in its current form.

Solutions:
- change the `fetch_size` on the driver side - which would reduce the page size `avg_blob_size * fetch_size` to be under 128Mb.
- increase said guardrails - to the risk of OOM'ing in case of concurrent access to the data - which would require to also increase the heap `Xmx` of Cassandra in such a case (up to half the RAM).

See the [Messaging documentation and resource limits](https://cassandra.apache.org/doc/4.0/cassandra/new/messaging.html#resource-limits-on-queued-messages)

## Scenario 2. Select count time-outs

The issue is described below:
[CASSANDRA-19949](https://issues.apache.org/jira/browse/CASSANDRA-19949)

`objcount.py` will run a **select count** query in this second scenario. This type of query is handled at coordinator level and differs from the first scenario, in that fetch_size won't help.
Cassandra 4.x has a performance problem which exhibit a 6 to 7 times slower execution time compared to 3.11 at the time this tool is written.

This requires an increase in the `range_request_timeout_in_ms` in Apach Cassandra ™️ 4.0, along a driver timeout change on the client

In the above case, we test the read of 100 000 rows with 10kb objects to see the performance.

The code contains an insert capability to test scenario 2 which will be described.
Uncomment **in a test environment only** the `gateway_insert()` around line 155 to reproduce [CASSANDRA-19949](https://issues.apache.org/jira/browse/CASSANDRA-19949)
**If running this tool in production, recommendation is to erase this line altogether from the `main` function** or make sure it's commented out.

# Example output and interpretation

On a 3 nodes cluster with RF3, with the queries executed by the client on a machine in the same network at LOCAL_QUORUM:

```
$ python3 ./objcount.py -c conf_dummy.ini -i 10.1.2.3 -k test -t count_perf
Using conf file: conf_dummy.ini
# SELECT #
Row count: 100000
Query timing with fetch 5000: 0:00:24.792389
Average row size: 10000.0
Max row size: 10000
Min row size: 10000

# COUNT #
57285970-80db-11ef-a9f3-e98cdf91d17f
Row count:100000
Count timing with fetch 5000: 0:00:14.189955
```

## SELECT section
In the above example, the SELECT section shows that retrieving the 100 000 records from the table via `SELECT key, blob FROM` took 24s. With an average blob size at 10kb.<br>
Note the "count" in this output is an iteration counter in the application of the rows retrieved and **not** a `SELECT COUNT`

The fetch is at default 5000.<br> 
The formula to calculate the number of pages is: `number of rows / fetch size = number of pages`<br>
In this scenario, `100 000 / 5 000 = 20` so we have 20 pages retrieved in this example.<br>
The query took 24 seconds to execute and would not time-out, as each page was retrieved in `execution time / number of pages = time to read a page`<br>
`24/20 = 1.02` which means the round trip for  each page is around ~1.02s (careful, this is an average, with dummy data, and even data with unique row per partition).<br>
**It is that value that matters in regards to the timeouts of DSE/C\***<br>

We can also define that the payload is `fetch_size * average row size` for a page, and `row_count * average row size` for the full query payload.<br>
Here the page size is `5 000 * 10 0000 = 50 000 000` or 50Mb.<br>
The query payload is `100 000 * 10 0000 = 1 000 000 000` or 1Gb.<br>

The **page size** is what affects the requirement for tweaking the `internode_application_` parameters in Cassandra 4.x<br>
Consider prior to this if the `fetch_size` can be reduced on the driver side.<br>

## COUNT section
When running the count, 3 information are output here:
- The trace_id - which was part of the debug info to generate CASSANDRA-19949
- The output of row count based on SELECT COUNT
- The execution time<br>

It is important to understand that this query is solely executed at coordinator level before the count result is fetch back to the application.<br>

This, with the default parameters of `range_request_timeout_in_ms` - default at 10s in C* 4.0 - and the python driver default timeout (10s as well) means this query would fail under normal condition as it takes 14s with this example. And so regardless of `fetch_size` in the driver.<br>

For this scenario, review both the `range_request_timeout` on C* and the driver query timeout to allow the query to succeed - until hopefully a fix for the Cassandra JIRA referenced.