import iperf3_runner
import signal
import sys

server = iperf3_runner.start_server()
print("iperf3 server running. Press Ctrl+C to stop.")

def shutdown(sig, frame):
    iperf3_runner.stop_server(server)
    print("Server stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)
signal.pause()