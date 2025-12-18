#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计llm_io文件夹下每个任务的progress平均值、状态与运行时间
"""

import os
import json
import argparse
import csv
from collections import defaultdict


def _latest_status_record(status_data):
    """提取game_status文件中最新的一条记录（兼容按step保存的格式）。"""
    if not isinstance(status_data, dict):
        return {}

    if status_data and all(isinstance(v, dict) for v in status_data.values()):
        # 按键（通常是step）排序，取最后一条
        def _sort_key(item):
            key = item[0]
            try:
                return (0, float(key))
            except (TypeError, ValueError):
                return (1, str(key))

        items = sorted(status_data.items(), key=_sort_key)
        return items[-1][1] if items else {}

    return status_data


def _parse_program_run_time(value):
    """将program_run_time字段解析为秒数的浮点值。"""
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.endswith("s"):
            cleaned = cleaned[:-1]
        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def analyze_task_progress(llm_io_path, model_name="llama"):
    """
    分析llm_io文件夹下每个任务的progress平均值、状态统计以及运行时间

    Args:
        llm_io_path: llm_io文件夹的路径

    Returns:
        tuple: (每个任务的平均progress值, status统计)
    """
    task_progress_data = defaultdict(list)
    task_status_counts = defaultdict(lambda: defaultdict(int))
    task_status_times = defaultdict(lambda: defaultdict(list))
    task_step_records = defaultdict(list)
    task_run_time_records = defaultdict(list)

    # 遍历所有任务文件夹
    for task_dir in os.listdir(llm_io_path):
        task_path = os.path.join(llm_io_path, task_dir)
        if not os.path.isdir(task_path):
            continue

        print(f"正在处理任务: {task_dir}")

        # 遍历该任务下的所有实验样本
        for experiment_dir in os.listdir(task_path):
            experiment_path = os.path.join(task_path, experiment_dir)
            if not os.path.isdir(experiment_path):
                continue

            # 遍历该实验样本下的所有agent
            for agent_dir in os.listdir(experiment_path):
                agent_path = os.path.join(experiment_path, agent_dir)
                if not os.path.isdir(agent_path):
                    continue

                # 查找tasks文件夹
                tasks_path = os.path.join(agent_path, "tasks")
                if not os.path.exists(tasks_path):
                    continue

                # 查找task_progress_llama.json文件
                progress_file = os.path.join(tasks_path, f"task_progress_{model_name}.json")
                if not os.path.exists(progress_file):
                    continue

                # 查找game_status_llama.json文件
                status_file = os.path.join(tasks_path, f"game_status_{model_name}.json")

                try:
                    # 读取progress JSON文件
                    with open(progress_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # 提取progress值
                    for agent_id, agent_data in data.items():
                        if isinstance(agent_data, dict):
                            for task_name, task_data in agent_data.items():
                                if isinstance(task_data, dict) and "progress" in task_data:
                                    progress = task_data["progress"]
                                    task_progress_data[task_name].append(progress)
                                    # print(f"  找到progress: {task_name} = {progress}")

                    # 读取status JSON文件
                    if os.path.exists(status_file):
                        with open(status_file, "r", encoding="utf-8") as f:
                            status_data = json.load(f)

                        latest_status = _latest_status_record(status_data)

                        status_value = latest_status.get("status") if isinstance(latest_status, dict) else None
                        if status_value:
                            # 按任务统计status - 使用当前任务目录名
                            task_status_counts[task_dir][status_value] += 1

                        current_time = latest_status.get("current_time") if isinstance(latest_status, dict) else None
                        if current_time is not None:
                            if status_value:
                                task_status_times[task_dir][status_value].append(current_time)
                            task_step_records[task_dir].append(
                                {
                                    "experiment_dir": experiment_dir,
                                    "agent_dir": agent_dir,
                                    "status": status_value or "unknown",
                                    "current_time": current_time,
                                    "program_run_time": _parse_program_run_time(
                                        latest_status.get("program_run_time") if isinstance(latest_status, dict) else None
                                    ),
                                    "relative_path": os.path.join(task_dir, experiment_dir, agent_dir),
                                }
                            )
                            # print(f"  找到status: {task_dir} - {status}, current_time: {current_time}")
                        # else:
                        # print(f"  找到status: {task_dir} - {status}")

                        run_time_value = None
                        if isinstance(latest_status, dict):
                            run_time_value = _parse_program_run_time(latest_status.get("program_run_time"))
                        if run_time_value is not None:
                            task_run_time_records[task_dir].append(
                                {
                                    "experiment_dir": experiment_dir,
                                    "agent_dir": agent_dir,
                                    "status": status_value or "unknown",
                                    "program_run_time": run_time_value,
                                    "relative_path": os.path.join(task_dir, experiment_dir, agent_dir),
                                }
                            )

                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"  错误: 无法解析文件 {progress_file} 或 {status_file}: {e}")
                    continue

    # 计算每个任务的平均progress
    task_averages = {}
    all_task_names = set(task_progress_data.keys()) | set(task_step_records.keys()) | set(task_run_time_records.keys())
    for task_name in all_task_names:
        progress_list = task_progress_data.get(task_name, [])
        if progress_list:
            avg_progress = sum(progress_list) / len(progress_list)
            task_averages[task_name] = {
                "average_progress": avg_progress,
                "sample_count": len(progress_list),
                "min_progress": min(progress_list),
                "max_progress": max(progress_list),
            }
        else:
            task_averages[task_name] = {"average_progress": 0.0, "sample_count": 0, "min_progress": 0.0, "max_progress": 0.0}

        step_records = task_step_records.get(task_name, [])
        step_values = [
            record["current_time"] for record in step_records if isinstance(record.get("current_time"), (int, float))
        ]
        if step_values:
            task_averages[task_name]["experiment_steps"] = {
                "average_steps": sum(step_values) / len(step_values),
                "sample_count": len(step_values),
                "min_steps": min(step_values),
                "max_steps": max(step_values),
                "details": step_records,
            }
        else:
            task_averages[task_name]["experiment_steps"] = {
                "average_steps": 0.0,
                "sample_count": 0,
                "min_steps": 0.0,
                "max_steps": 0.0,
                "details": [],
            }

        # 计算程序运行时间统计
        run_records = task_run_time_records.get(task_name, [])
        run_values = [
            record["program_run_time"] for record in run_records if isinstance(record.get("program_run_time"), (int, float))
        ]
        if run_values:
            task_averages[task_name]["program_run_time"] = {
                "average_run_time": sum(run_values) / len(run_values),
                "sample_count": len(run_values),
                "min_run_time": min(run_values),
                "max_run_time": max(run_values),
                "details": run_records,
            }
        else:
            task_averages[task_name]["program_run_time"] = {
                "average_run_time": 0.0,
                "sample_count": 0,
                "min_run_time": 0.0,
                "max_run_time": 0.0,
                "details": [],
            }

    # 计算每个任务每种状态的平均时间
    task_status_avg_times = {}
    for task_name, status_times in task_status_times.items():
        task_status_avg_times[task_name] = {}
        for status, times in status_times.items():
            if times:
                avg_time = sum(times) / len(times)
                task_status_avg_times[task_name][status] = {
                    "average_time": avg_time,
                    "sample_count": len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                }
            else:
                task_status_avg_times[task_name][status] = {
                    "average_time": 0.0,
                    "sample_count": 0,
                    "min_time": 0.0,
                    "max_time": 0.0,
                }

    return task_averages, dict(task_status_counts), task_status_avg_times


def sanitize_status_column_name(status):
    """将状态名转换为适合CSV列名的形式"""
    sanitized = "".join(ch.lower() if ch.isalnum() else "_" for ch in status.strip())
    sanitized = sanitized.strip("_")
    return sanitized or "status"


def save_results_csv(results, task_status_stats, task_status_times, output_path):
    """将分析结果保存为CSV格式"""
    status_set = set()
    for status_dict in task_status_stats.values():
        status_set.update(status_dict.keys())
    for status_dict in task_status_times.values():
        status_set.update(status_dict.keys())

    status_list = sorted(status_set)
    sanitized_names = {status: sanitize_status_column_name(status) for status in status_list}

    fieldnames = [
        "task_name",
        "average_progress",
        "progress_sample_count",
        "min_progress",
        "max_progress",
        "average_steps",
        "steps_sample_count",
        "min_steps",
        "max_steps",
        "average_program_run_time",
        "program_run_time_sample_count",
        "min_program_run_time",
        "max_program_run_time",
    ]

    for status in status_list:
        prefix = f"status_{sanitized_names[status]}"
        fieldnames.extend(
            [f"{prefix}_count", f"{prefix}_avg_time", f"{prefix}_min_time", f"{prefix}_max_time", f"{prefix}_time_samples"]
        )

    task_names = sorted(results.keys())

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for task_name in task_names:
            data = results.get(task_name, {})
            steps = data.get("experiment_steps", {})
            run_time = data.get("program_run_time", {})
            row = {
                "task_name": task_name,
                "average_progress": data.get("average_progress", 0.0),
                "progress_sample_count": data.get("sample_count", 0),
                "min_progress": data.get("min_progress", 0.0),
                "max_progress": data.get("max_progress", 0.0),
                "average_steps": steps.get("average_steps", 0.0),
                "steps_sample_count": steps.get("sample_count", 0),
                "min_steps": steps.get("min_steps", 0.0),
                "max_steps": steps.get("max_steps", 0.0),
                "average_program_run_time": run_time.get("average_run_time", 0.0),
                "program_run_time_sample_count": run_time.get("sample_count", 0),
                "min_program_run_time": run_time.get("min_run_time", 0.0),
                "max_program_run_time": run_time.get("max_run_time", 0.0),
            }

            status_counts = task_status_stats.get(task_name, {})
            status_times = task_status_times.get(task_name, {})

            for status in status_list:
                prefix = f"status_{sanitized_names[status]}"
                row[f"{prefix}_count"] = status_counts.get(status, 0)
                time_stats = status_times.get(status, {})
                row[f"{prefix}_avg_time"] = time_stats.get("average_time", 0.0)
                row[f"{prefix}_min_time"] = time_stats.get("min_time", 0.0)
                row[f"{prefix}_max_time"] = time_stats.get("max_time", 0.0)
                row[f"{prefix}_time_samples"] = time_stats.get("sample_count", 0)
            
            writer.writerow(row)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="统计llm_io文件夹下每个任务的progress、状态与运行时间")
    parser.add_argument("llm_io_path", help="llm_io数据所在的路径")
    parser.add_argument("--model_name", default="llama", help="模型名称，默认为llama")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    llm_io_path = os.path.join("llm_io", args.llm_io_path)
    model_name = args.model_name

    if not os.path.exists(llm_io_path):
        print(f"错误: 路径 {llm_io_path} 不存在")
        return

    print("开始分析任务进度...")
    print("=" * 60)

    # 分析任务进度和状态
    results, task_status_stats, task_status_times = analyze_task_progress(llm_io_path, model_name)

    print("\n" + "=" * 60)
    print("任务分析结果:")
    print("=" * 60)

    # 按平均progress排序
    sorted_results = sorted(results.items(), key=lambda x: x[1]["average_progress"], reverse=True)

    for task_name, data in sorted_results:
        print(f"\n任务: {task_name}")
        print(f"  平均完成率: {data['average_progress']:.4f} ({data['average_progress']*100:.2f}%)")
        print(f"  样本数量: {data['sample_count']}")
        print(f"  最小完成率: {data['min_progress']:.4f} ({data['min_progress']*100:.2f}%)")
        print(f"  最大完成率: {data['max_progress']:.4f} ({data['max_progress']*100:.2f}%)")

        run_time_stats = data.get("program_run_time", {})
        if run_time_stats.get("sample_count", 0) > 0:
            print(
                f"  平均运行时间: {run_time_stats['average_run_time']:.2f}s "
                f"(范围: {run_time_stats['min_run_time']:.2f}s - {run_time_stats['max_run_time']:.2f}s, "
                f"样本: {run_time_stats['sample_count']})"
            )

        # 显示该任务的状态统计
        if task_name in task_status_stats:
            print(f"  游戏状态分布:")
            status_counts = task_status_stats[task_name]
            total_count = sum(status_counts.values())
            for status, count in sorted(status_counts.items()):
                percentage = (count / total_count * 100) if total_count > 0 else 0
                print(f"    {status}: {count}个 ({percentage:.1f}%)")

                # 显示该状态的时间统计
                if task_name in task_status_times and status in task_status_times[task_name]:
                    time_stats = task_status_times[task_name][status]
                    if time_stats["sample_count"] > 0:
                        print(f"      平均时间: {time_stats['average_time']:.1f}")
                        print(f"      时间范围: {time_stats['min_time']:.1f} - {time_stats['max_time']:.1f}")
        print()

    # 保存结果到文件
    output_data = {
        "task_progress": results,
        "task_status_statistics": task_status_stats,
        "task_status_times": task_status_times,
    }
    output_file = os.path.join(llm_io_path, "task_progress_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_file}")

    csv_file = os.path.join(llm_io_path, f"task_progress_analysis_{model_name}.csv")
    save_results_csv(results, task_status_stats, task_status_times, csv_file)
    print(f"CSV结果已保存到: {csv_file}")


if __name__ == "__main__":
    main()
