import argparse
from typing import Optional

def run_ping(server_ip, port: int = 5201, extra_args=[]):
    import subprocess
    import time
    args = ["ping", "-q", server_ip] + extra_args

    # Run ping command and capture output
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        print("Ping failed: {}".format(stderr.decode()))
        return

    return stdout.decode().strip()

def parse_rtt_avg(ping_output: str) -> Optional[float]:
    # ping -q summary line looks like:
    # rtt min/avg/max/mdev = 1.234/2.345/3.456/0.123 ms
    import re
    match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', ping_output)
    if match:
        return float(match.group(1))
    return None

def parse_packet_loss(ping_output: str) -> Optional[float]:
    # summary line looks like:
    # 4 packets transmitted, 4 received, 0% packet loss, time 3004ms
    import re
    match = re.search(r'(\d+)% packet loss', ping_output)
    if match:
        return float(match.group(1))
    return None

def parse_args():
    parser = argparse.ArgumentParser(description='Run iperf3 tests')
    parser.add_argument('-t', '--test_name',        type=str, default='Test_05_08_1')
    parser.add_argument('-e', '--environment',       type=str, default='LoS')
    parser.add_argument('-d', '--distance',          type=float, default=10.0)
    parser.add_argument('-s', '--packet_size',       type=int,   default=1024)
    parser.add_argument('-n', '--number_of_packets', type=int,   default=100)
    parser.add_argument('-D', '--duration',          type=float, default=60.0)
    parser.add_argument('-i', '--iterations',        type=int,   default=1, help='Number of times to repeat the test')
    parser.add_argument('--server_ip', type=str, default='localhost',
                    help='IP address of the iperf3 server')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    server_ip = args.server_ip
    extra_args = ["-c", "4", "-i", "0.02"]  # Example: ping 4 times
    result = run_ping(server_ip, extra_args=extra_args)
    print(result)
