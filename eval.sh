#!/bin/bash

# timeout 5s python3 main.py open_tests/max2.sl
for file in open_tests/*; do
    echo "Testing" $file
    timeout 10s python3 main.py $file
done
