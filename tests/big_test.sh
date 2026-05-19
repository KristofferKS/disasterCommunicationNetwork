#!/bin/bash

# ============================================================
# run_all_tests.sh
# Runs all combinations of iperf3_tester.py parameters
# Usage: ./run_all_tests.sh [--host_ip <ip>] [--output <file>]
# ============================================================

HOST="localhost"
OUTPUT="results.txt"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host_ip) HOST="$2"; shift 2 ;;
        --output)  OUTPUT="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ============================================================
# Parameter lists — edit these to change what gets tested
# ============================================================
declare -a PROTOS=("udp" "tcp")
declare -a PKT_SIZES=("16" "128" "512" "1024")
declare -a PKTS=("200" "400" "600" "800" "1000")
declare -a PPS_VALUES=("20" "40" "60" "80" "100")
declare -a BURST_MODES=("normal" "burst")

# Burst-specific parameters (only used when burst mode is active)
declare -a MIN_GAPS=("0.1" "0.5")
declare -a MAX_GAPS=("1.0" "3.0")
declare -a MIN_BURSTS=("1" "3")
declare -a MAX_BURSTS=("5" "10")
# ============================================================

# Count total tests
normal_tests=$(( ${#PROTOS[@]} * ${#PKT_SIZES[@]} * ${#PKTS[@]} * ${#PPS_VALUES[@]} ))
burst_tests=$(( ${#PROTOS[@]} * ${#PKT_SIZES[@]} * ${#PKTS[@]} * ${#MIN_GAPS[@]} * ${#MAX_GAPS[@]} * ${#MIN_BURSTS[@]} * ${#MAX_BURSTS[@]} ))
total_tests=$(( normal_tests + burst_tests ))

echo "============================================"
echo " iperf3 full combination test"
echo " Host:         $HOST"
echo " Normal tests: $normal_tests"
echo " Burst tests:  $burst_tests"
echo " Total:        $total_tests"
echo " Output:       $OUTPUT"
echo "============================================"
echo ""

> "$OUTPUT"
current_test=1

# ---- Normal mode ----
for proto in "${PROTOS[@]}"; do
    for pkt_size in "${PKT_SIZES[@]}"; do
        for pkts in "${PKTS[@]}"; do
            for pps in "${PPS_VALUES[@]}"; do
                echo "[$current_test/$total_tests] proto=$proto size=$pkt_size pkts=$pkts pps=$pps"
                echo "--- [$current_test/$total_tests] proto=$proto size=$pkt_size pkts=$pkts pps=$pps ---" >> "$OUTPUT"
                python3 tester.py \
                    --host "$HOST" \
                    --proto "$proto" \
                    --pkt-size "$pkt_size" \
                    --pkts "$pkts" \
                    --pps "$pps" >> "$OUTPUT" 2>&1
                echo "" >> "$OUTPUT"
                ((current_test++))
                sleep 0.5
            done
        done
    done
done

# ---- Burst mode ----
for proto in "${PROTOS[@]}"; do
    for pkt_size in "${PKT_SIZES[@]}"; do
        for pkts in "${PKTS[@]}"; do
            for min_gap in "${MIN_GAPS[@]}"; do
                for max_gap in "${MAX_GAPS[@]}"; do
                    # Skip if min_gap >= max_gap
                    if (( $(echo "$min_gap >= $max_gap" | bc -l) )); then
                        continue
                    fi
                    for min_burst in "${MIN_BURSTS[@]}"; do
                        for max_burst in "${MAX_BURSTS[@]}"; do
                            # Skip if min_burst >= max_burst
                            if (( min_burst >= max_burst )); then
                                continue
                            fi
                            echo "[$current_test/$total_tests] proto=$proto size=$pkt_size pkts=$pkts burst min_gap=$min_gap max_gap=$max_gap min_b=$min_burst max_b=$max_burst"
                            echo "--- [$current_test/$total_tests] proto=$proto size=$pkt_size pkts=$pkts burst min_gap=$min_gap max_gap=$max_gap min_b=$min_burst max_b=$max_burst ---" >> "$OUTPUT"
                            python3 tester.py \
                                --host "$HOST" \
                                --proto "$proto" \
                                --pkt-size "$pkt_size" \
                                --pkts "$pkts" \
                                --burst \
                                --min-gap "$min_gap" \
                                --max-gap "$max_gap" \
                                --min-burst "$min_burst" \
                                --max-burst "$max_burst" >> "$OUTPUT" 2>&1
                            echo "" >> "$OUTPUT"
                            ((current_test++))
                            sleep 0.5
                        done
                    done
                done
            done
        done
    done
done

echo ""
echo "============================================"
echo " All tests done. Results saved to $OUTPUT"
echo "============================================"