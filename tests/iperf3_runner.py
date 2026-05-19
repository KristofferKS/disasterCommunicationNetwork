import subprocess
import time


def start_server(port: int = 5201):
    # Kill any existing iperf3 first
    subprocess.run(["sudo", "pkill", "iperf3"], check=False)
    time.sleep(0.5) # Give it a moment to ensure the process is killed
    # Start the iperf3 server in the background
    proc = subprocess.Popen(["iperf3", "-s", "-p", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1) # Give the server a moment to start
    return proc


def run_client(server_ip, port: int = 5201, extra_args=None):
    if extra_args is None:
        extra_args = []
    args = ["iperf3", "-c", server_ip, "-p", str(port), "-J"] + extra_args
    try:
        val = subprocess.check_output(args, stderr=subprocess.STDOUT).decode('utf-8').strip()
        return val
    except subprocess.CalledProcessError as exc:
        output = exc.output.decode('utf-8', errors='replace').strip() if exc.output else ''
        raise RuntimeError("iperf3 failed with exit code {}\n{}".format(exc.returncode, output))

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