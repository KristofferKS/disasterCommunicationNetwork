import subprocess
import time

def start_server(port: int = 5201):
    # Kill any existing iperf3 first
    subprocess.run(["sudo", "pkill", "iperf3"], check=False)
    time.sleep(0.5) # Give it a moment to ensure the process is killed
    # Start the iperf3 server in the background
    proc = subprocess.Popen(["iperf3", "-s", "-p", str(port)])
    time.sleep(1) # Give the server a moment to start
    return proc

def run_client(server_ip, port: int = 5201, extra_args=[]):
    args = ["iperf3", "-c", server_ip, "-p", str(port), "-J"] + extra_args
    val = subprocess.check_output(args).decode('utf-8').strip()
    return val

def stop_server(proc):
    proc.terminate()
    proc.wait()

if __name__ == '__main__':
    server = start_server()
    try:
        result = run_client("localhost", extra_args=["-t", "2"])
        print(result)
    finally:
        stop_server(server)