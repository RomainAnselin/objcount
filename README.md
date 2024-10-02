README

The `objcount.py` is a program written to review a number of statistics for specific queries in Cassandra.

It attempts to test specific use cases which are known to be problematic in Cassandra 4.x

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
---
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

---
## Scenario 2. Select count time-outs

The issue is described below:
[CASSANDRA-19949](https://issues.apache.org/jira/browse/CASSANDRA-19949)

Objcount.py will run a select count query after scenario 1. This is handled at coordinator level and differs from the first scenario, in that fetch size won't help.
Cassandra 4.x has a performance problem which exhibit a 6 to 7 times slower execution time.

This requires an increase in the `range_request_timeout_in_ms` in Apach Cassandra ™️ 4.0, along a driver timeout change on the client

In the above case, we test the read of 100 000 rows with 10kb objects to see the performance.

The code contains an insert capability to test scenario 2 which will be described.
Uncomment **in a test environment only** the `gateway_insert()` around line 155 to reproduce [CASSANDRA-19949](https://issues.apache.org/jira/browse/CASSANDRA-19949)
**If running this tool in production, recommendation is to erase this line altogether from the `main` function** or make sure it's commented out.

