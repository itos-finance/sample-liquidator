# Super Simple Event Listener

Listens to events from a contract from a url.
The url can be configered in SimpleEventListener, but if you're just using local
host you can configure the port from the command line option --port.
Listened to events will be aggregated and posted to a local endpoint.

Example usage:
`./SimpleEventListener.py {contract_addr} -p 4321`

The only required argument is the contract addr.

There is a local flag that allows for local testing. Instead of posting the data
to the endpoint, it just directly graphs the data in matplotlib. Ctrl+C after
closing the graph to exit out of that loop. You have 5 seconds between new
graphs.
