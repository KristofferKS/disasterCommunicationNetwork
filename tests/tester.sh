#!/bin/bash

declare -a size=(
    "16"
    "32"
    "64"
    "128"
    "256"
    "512"
    "1024"
    "2048"
)

declare -a number_of_packets=(
    "100"
    "200"
    "300"
    "400"
    "500"
    "600"
    "700"
    "800"
    "900"
    "1000"
)

total_tests=$(( ${#size[@]} * ${#number_of_packets[@]} ))
current_test=1

for s in "${size[@]}"
do
    for n in "${number_of_packets[@]}"
    do
        echo "Testing with size: $s and number of packets: $n ($current_test/$total_tests)"
        python3 client.py -d "$1" -s "$s" -n "$n"
        ((current_test++))
    done
done

