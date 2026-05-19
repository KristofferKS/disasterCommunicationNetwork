#!/usr/bin/env python3
"""
iperf3 test configurator
Supports UDP/TCP, custom packet size, packet count, pacing, and random bursts.
Saves results to database like client.py.
"""

import subprocess
import time
import random
import argparse
import json
import sys

import iperf3_runner
import bigger_database
import ping_runner

def run_iperf3(host, proto, pkt_size, total_bytes, bitrate, pacing_us, interval):
    extra = ["-l", str(pkt_size), "-n", str(total_bytes)]
    if proto == "udp":
        extra += ["-u", "-b", "10G"]
    if interval:
        extra += ["-i", str(interval)]
    print("Running iperf3 ({}) l={} n={} b={} pacing={}µs".format(
        proto, pkt_size, total_bytes, bitrate, pacing_us
    ))
    raw = iperf3_runner.run_client(host, extra_args=extra)
    return json.loads(raw)


def run_burst(host, proto, pkt_size, total_pkts, min_gap, max_gap, min_burst, max_burst):
    results = []
    sent = 0
    while sent < total_pkts:
        burst_n = random.randint(min_burst, min(max_burst, total_pkts - sent))
        bytes_n = pkt_size * burst_n
        extra = ["-l", str(pkt_size), "-n", str(bytes_n), "-b", "0"]
        if proto == "udp":
            extra.append("-u")
        print("Sending burst of {} packet(s) ({}/{} total)...".format(
            burst_n, sent + burst_n, total_pkts
        ))
        raw = iperf3_runner.run_client(host, extra_args=extra)
        results.append(json.loads(raw))
        sent += burst_n
        if sent < total_pkts:
            gap = random.uniform(min_gap, max_gap)
            print("  waiting {:.2f}s before next burst".format(gap))
            time.sleep(gap)
    print("Burst done.")
    return results


def extract_stats(data):
    end = data["end"]["sum"]
    return {
        "throughput":   end["bits_per_second"],
        "jitter_ms":    end.get("jitter_ms", 0),
        "packet_loss":  end.get("lost_percent", 0),
        "duration":     end.get("seconds", 0),
    }


def merge_burst_stats(results):
    """Average stats across all burst sub-results."""
    if not results:
        return {"throughput": 0, "jitter_ms": 0, "packet_loss": 0, "duration": 0}
    keys = ["throughput", "jitter_ms", "packet_loss", "duration"]
    merged = {}
    for k in keys:
        vals = [extract_stats(r)[k] for r in results]
        merged[k] = sum(vals) / len(vals)
    merged["duration"] = sum(extract_stats(r)["duration"] for r in results)
    return merged


def main():
    parser = argparse.ArgumentParser(
        description="iperf3 test configurator — UDP/TCP, pacing, and random bursts"
    )
    parser.add_argument("-t", "--test_name",        type=str,   default="Test_tester")
    parser.add_argument("-e", "--environment",       type=str,   default="LoS")
    parser.add_argument("-d", "--distance",          type=float, default=10.0)
    parser.add_argument("-H", "--height",            type=float, default=None, help="Height value")
    parser.add_argument("--host",                    type=str,   default="localhost")
    parser.add_argument("--proto",   choices=["udp", "tcp"],     default="udp")
    parser.add_argument("--pkt-size",  type=int,   default=16,   help="Packet size in bytes")
    parser.add_argument("--pkts",      type=int,   default=100,  help="Total number of packets")
    parser.add_argument("--pps",       type=int,   default=1,    help="Packets per second (non-burst mode)")
    parser.add_argument("--interval",  type=int,   default=1,    help="Report interval in seconds")
    parser.add_argument("-i", "--iterations", type=int, default=10, help="Number of times to repeat the test")
    parser.add_argument("--burst",      action="store_true",     help="Enable random burst mode")
    parser.add_argument("--min-gap",   type=float, default=0.5,  help="Min gap between bursts (s)")
    parser.add_argument("--max-gap",   type=float, default=3.0,  help="Max gap between bursts (s)")
    parser.add_argument("--min-burst", type=int,   default=1,    help="Min packets per burst")
    parser.add_argument("--max-burst", type=int,   default=5,    help="Max packets per burst")

    args = parser.parse_args()

    # Derived values
    pkt_size    = args.pkt_size
    total_pkts  = args.pkts
    total_bytes = pkt_size * total_pkts
    bitrate     = pkt_size * 8 * args.pps
    pacing_us   = max(1, 1000000 // args.pps)

    conn = bigger_database.get_conn()
    try:
        test_id = bigger_database.insert_test(conn, args)
        print("Test '{}' started (id={}), running {} iteration(s)...\n".format(
            args.test_name, test_id, args.iterations
        ))

        ping_output = ping_runner.run_ping(args.host, extra_args=["-c", "4"])
        rtt_ms = ping_runner.parse_rtt_avg(ping_output) if ping_output else None

        for i in range(args.iterations):
            print("  Iteration {}/{}...".format(i + 1, args.iterations))

            if args.burst:
                results = run_burst(
                    args.host, args.proto, pkt_size, total_pkts,
                    args.min_gap, args.max_gap, args.min_burst, args.max_burst
                )
                stats = merge_burst_stats(results)
            else:
                data = run_iperf3(
                    args.host, args.proto, pkt_size, total_bytes,
                    bitrate, pacing_us, args.interval
                )
                stats = extract_stats(data)

            bigger_database.insert_iteration(
                conn, test_id, i + 1,
                stats["throughput"],
                stats["jitter_ms"],
                stats["packet_loss"],
                stats["duration"],
                rtt_ms
            )

        bigger_database.insert_averages(conn, test_id)
        avg = bigger_database.get_averages(conn, test_id)
        print("\nAverages over {} iteration(s):".format(args.iterations))
        print("  Throughput: {:.2f} bps  ({:.3f} kbps)".format(
            avg['throughput'], avg['throughput'] / 1000
        ))
        print("  Jitter:     {:.3f} ms".format(avg['jitter_ms']))
        print("  Loss:       {:.2f}%".format(avg['packet_loss_iperf']))
        print("  RTT:        {:.3f} ms".format(avg['rtt_ms']))
        print("  Duration:   {:.2f} s".format(avg['duration']))

    finally:
        conn.close()


if __name__ == "__main__":
    main()