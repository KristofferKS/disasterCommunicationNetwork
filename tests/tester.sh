#!/bin/bash

declare -a size=(
    "16"
    "32"
    "64"
)

declare -a freq=(
    "1"
    "2"
    "5"
    "10"
    "25"
    "50"
    "100"
)
total_tests=$(( ${#size[@]} * ${#freq[@]} ))
current_test=1

for s in "${size[@]}"
do
    for n in "${freq[@]}"
    do
        echo "Testing with size: $s and number of packets: $n ($current_test/$total_tests)"
        python3 main.py -t "$1" -e "$2" -d "$3" -s "$s" -n "$n" -i "$4"
        ((current_test++))
    done
done

