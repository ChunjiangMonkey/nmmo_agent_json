#!/bin/bash

parallel_jobs=1
exp_num=1
config_name="single_task"

simple_tasks=("attain_Melee_level_10" "attain_Alchemy_level_10" "attain_Herbalism_level_10" "harvest_Arrow_level_1_20" "consume_Ration_level_1_20" "equip_Top_level_1" "equip_Rod_level_1" "equip_Spear_level_1" "fully_armed_Melee_level_1" "defeat_npc_level_1_20")
difficult_tasks=("defeat_npc_level_3_20" "harvest_Arrow_level_3_20" "consume_Ration_level_3_20" "equip_Top_level_3" "equip_Rod_level_3" "equip_Spear_level_3" "fully_armed_Melee_level_3")

tasks=("attain_Melee_level_10" "attain_Alchemy_level_10" "attain_Herbalism_level_10" "harvest_Arrow_level_1_20" "consume_Ration_level_1_20" "equip_Top_level_1" "equip_Rod_level_1" "equip_Spear_level_1" "fully_armed_Melee_level_1" "defeat_npc_level_1_20" "defeat_npc_level_3_20" "harvest_Arrow_level_3_20" "consume_Ration_level_3_20" "equip_Top_level_3" "equip_Rod_level_3" "equip_Spear_level_3" "fully_armed_Melee_level_3")

timestamp=$(date +"%Y-%m-%d_%H-%M-%S")

for task in "${tasks[@]}"; do
    if [[ " ${simple_tasks[*]} " =~ " ${task} " ]]; then
        nick_name="run_simple_task"
    elif [[ " ${difficult_tasks[*]} " =~ " ${task} " ]]; then
        nick_name="run_difficult_task"
    else
        echo "Task ${task} not found in simple or difficult lists, skipping." >&2
        continue
    fi

    exp_name="${timestamp}_${nick_name}"
    for pid in $(seq 1 $exp_num); do
        echo "python main.py --exp_name=$exp_name --goal=$task --pid=$pid --config_name=$config_name --debug"
    done
done | parallel -j "${parallel_jobs}" --ungroup
