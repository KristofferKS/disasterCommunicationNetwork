import argparse
import json
import iperf3_runner
import database

def parse_args():
    parser = argparse.ArgumentParser(description='Run iperf3 tests')
    parser.add_argument('-t', '--test_name',        type=str)
    parser.add_argument('-e', '--environment',       type=str)
    parser.add_argument('-d', '--distance',          type=float, default=10.0)
    parser.add_argument('-s', '--packet_size',       type=int,   default=1024)
    parser.add_argument('-n', '--number_of_packets', type=int,   default=100)
    parser.add_argument('-D', '--duration',          type=float, default=60.0)
    parser.add_argument('-i', '--iterations',        type=int,   default=1, help='Number of times to repeat the test')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    total_bytes = args.packet_size * args.number_of_packets

    conn = database.get_conn()
    server = iperf3_runner.start_server()
    try:
        test_id = database.insert_test(conn, args)
        print(f"Test '{args.test_name}' started (id={test_id}), running {args.iterations} iteration(s)...\n")

        for i in range(args.iterations):
            print(f"  Iteration {i + 1}/{args.iterations}...")
            raw = iperf3_runner.run_client(
                "localhost",
                extra_args=["-u", "-l", str(args.packet_size), "-n", str(total_bytes)]
            )

            data = json.loads(raw)
            end = data["end"]["sum"]

            throughput  = end["bits_per_second"]
            jitter_ms   = end.get("jitter_ms", 0)
            packet_loss = end.get("lost_percent", 0)
            duration    = end.get("seconds", 0)

            database.insert_iteration(conn, test_id, i + 1, throughput, jitter_ms, packet_loss, duration)
            print(f"    Throughput: {throughput/1e6:.2f} Mbps  Jitter: {jitter_ms:.3f} ms  Loss: {packet_loss:.2f}% Duration: {duration:.2f} s")

        database.insert_averages(conn, test_id)
        avg = database.get_averages(conn, test_id)
        print(f"\nAverages over {args.iterations} iteration(s):")
        print(f"  Throughput: {avg['throughput']/1e6:.2f} Mbps")
        print(f"  Jitter:     {avg['jitter_ms']:.3f} ms")
        print(f"  Loss:       {avg['packet_loss']:.2f}%")
        print(f"  Duration:   {avg['duration']:.2f} s")

    finally:
        iperf3_runner.stop_server(server)
        conn.close()