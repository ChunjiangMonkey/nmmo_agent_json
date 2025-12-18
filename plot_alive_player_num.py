import argparse
import json
from pathlib import Path
from typing import List, Tuple

try:
    import matplotlib.pyplot as plt  # type: ignore
except ImportError:  # matplotlib is optional; fall back to SVG output.
    plt = None


DEFAULT_INPUTS = [
    Path("llm_io/2025-12-11_23-07-10_test_individual/1/0/tasks/game_status_llama.json"),
    Path("llm_io/2025-12-11_23-07-10_test_competitior/1/0/tasks/game_status_llama.json"),
    Path("llm_io/2025-12-11_23-07-10_test_cooperation/1/0/tasks/game_status_llama.json"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot alive_player_num over time from one or more game_status_llama.json files.",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        nargs="+",
        default=DEFAULT_INPUTS,
        help="Paths to game_status_llama.json files. Defaults to the three specified runs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("alive_player_num_multi.svg"),
        help="Where to save the generated plot (png if matplotlib is installed, otherwise svg).",
    )
    return parser.parse_args()


def load_points(path: Path) -> List[Tuple[float, float]]:
    with path.open() as f:
        payload = json.load(f)

    points: List[Tuple[float, float]] = []
    for _, entry in payload.items():
        if not isinstance(entry, dict):
            continue
        time_val = entry.get("current_time")
        alive_val = entry.get("alive_player_num")
        if time_val is None or alive_val is None:
            continue
        points.append((float(time_val), float(alive_val)))

    points.sort(key=lambda item: item[0])
    return points


def plot(series: List[Tuple[str, List[Tuple[float, float]]]], output_path: Path) -> None:
    all_points = [(t, a) for _, pts in series for t, a in pts]
    if not all_points:
        raise ValueError("No data points found with current_time and alive_player_num.")

    if output_path.suffix.lower() == ".png" and plt is None:
        fallback_path = output_path.with_suffix(".svg")
        print("matplotlib not installed; writing SVG instead.")
        write_svg(series, fallback_path)
        print(f"Saved plot to {fallback_path.resolve()}")
        return

    if plt is None or output_path.suffix.lower() == ".svg":
        write_svg(series, output_path)
        print(f"Saved plot to {output_path.resolve()}")
        return

    plt.figure(figsize=(10, 5))
    for label, pts in series:
        times = [p[0] for p in pts]
        alive_counts = [p[1] for p in pts]
        plt.plot(times, alive_counts, marker="o", linewidth=2, label=label)
    plt.title("alive_player_num over time")
    plt.xlabel("current_time")
    plt.ylabel("alive_player_num")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Saved plot to {output_path.resolve()}")


def write_svg(series: List[Tuple[str, List[Tuple[float, float]]]], output_path: Path) -> None:
    width, height, margin = 950, 480, 70
    times = [t for _, pts in series for t, _ in pts]
    alive_counts = [a for _, pts in series for _, a in pts]

    min_x, max_x = min(times), max(times)
    min_y, max_y = min(alive_counts), max(alive_counts)
    if max_x == min_x:
        max_x += 1.0
    if max_y == min_y:
        max_y += 1.0

    def scale_x(x: float) -> float:
        return margin + (x - min_x) / (max_x - min_x) * (width - 2 * margin)

    def scale_y(y: float) -> float:
        return height - margin - (y - min_y) / (max_y - min_y) * (height - 2 * margin)

    palette = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477"]

    horizontal_grid = []
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        val = min_y + frac * (max_y - min_y)
        y = scale_y(val)
        horizontal_grid.append(
            f'<line x1="{margin}" y1="{y:.2f}" x2="{width - margin}" y2="{y:.2f}" '
            f'stroke="#e0e0e0" stroke-width="1"/>'
        )
        horizontal_grid.append(
            f'<text x="{margin - 12}" y="{y + 4:.2f}" font-size="12" text-anchor="end" fill="#555">{val:.2f}</text>'
        )

    vertical_grid = []
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        val = min_x + frac * (max_x - min_x)
        x = scale_x(val)
        vertical_grid.append(
            f'<line x1="{x:.2f}" y1="{margin}" x2="{x:.2f}" y2="{height - margin}" '
            f'stroke="#e0e0e0" stroke-width="1"/>'
        )
        vertical_grid.append(
            f'<text x="{x:.2f}" y="{height - margin + 22}" font-size="12" text-anchor="middle" fill="#555">{val:.2f}</text>'
        )

    series_parts: List[str] = []
    for idx, (label, pts) in enumerate(series):
        color = palette[idx % len(palette)]
        poly_points = " ".join(f"{scale_x(x):.2f},{scale_y(y):.2f}" for x, y in pts)
        circles = "\n    ".join(
            f'<circle cx="{scale_x(x):.2f}" cy="{scale_y(y):.2f}" r="3" fill="{color}" />' for x, y in pts
        )
        series_parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{poly_points}"/>\n    {circles}'
        )

    legend_items = []
    legend_x, legend_y = width - margin - 150, margin
    for idx, (label, _) in enumerate(series):
        color = palette[idx % len(palette)]
        y = legend_y + idx * 20
        legend_items.append(
            f'<rect x="{legend_x}" y="{y - 10}" width="12" height="12" fill="{color}" />'
            f'<text x="{legend_x + 18}" y="{y}" font-size="12" fill="#111">{label}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>
  <g>
    {''.join(horizontal_grid)}
    {''.join(vertical_grid)}
  </g>
  <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#000" stroke-width="1.5"/>
  <line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#000" stroke-width="1.5"/>
  {' '.join(series_parts)}
  <g>
    {''.join(legend_items)}
  </g>
  <text x="{width/2:.2f}" y="32" font-size="16" text-anchor="middle" fill="#111">alive_player_num over time</text>
  <text x="{width/2:.2f}" y="{height - 18}" font-size="14" text-anchor="middle" fill="#111">current_time</text>
  <text x="18" y="{height/2:.2f}" font-size="14" text-anchor="middle" fill="#111" transform="rotate(-90 18 {height/2:.2f})">alive_player_num</text>
</svg>
"""
    output_path.write_text(svg)


def derive_label(path: Path) -> str:
    """Prefer the run folder name (three levels up from tasks), else use the file name."""
    try:
        return path.parents[3].name
    except IndexError:
        return path.stem


def main() -> None:
    args = parse_args()
    series: List[Tuple[str, List[Tuple[float, float]]]] = []
    for path in args.inputs:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        label = derive_label(path)
        series.append((label, load_points(path)))
    plot(series, args.output)


if __name__ == "__main__":
    main()
