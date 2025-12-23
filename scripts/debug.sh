#!/bin/bash

parallel_jobs=1
exp_num=2
config_name="debug"
timestamp=$(date +"%Y-%m-%d_%H-%M-%S")
nick_name="Debug"
exp_name="${timestamp}_${nick_name}"
for pid in $(seq 1 $exp_num); do
    echo "python main.py --exp_name=$exp_name --run_survive --pid=$pid --config_name=$config_name --debug"
done | parallel -j "${parallel_jobs}" --ungroup
