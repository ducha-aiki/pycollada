#!/usr/bin/env python3
"""
Benchmark pycollada DAE loading performance.

Usage:
    python examples/benchmark_dae_load.py <dae_file> [--runs N]
    
Examples:
    python examples/benchmark_dae_load.py myfile.dae
    python examples/benchmark_dae_load.py myfile.dae --runs 20
"""

import argparse
import time
from pathlib import Path
import collada


def benchmark_load(dae_path: str, num_runs: int = 10):
    """Benchmark DAE loading and print timing results."""
    
    path = Path(dae_path)
    if not path.exists():
        print(f"Error: File not found: {dae_path}")
        return
    
    file_size_mb = path.stat().st_size / (1024 * 1024)
    
    print(f"File: {path.name}")
    print(f"Size: {file_size_mb:.2f} MB")
    print(f"Runs: {num_runs}")
    print("-" * 40)
    
    # Warm-up run and get DAE info
    dae = collada.Collada(dae_path)
    n_geom = len(dae.geometries) if hasattr(dae, 'geometries') else 0
    n_cam = len(dae.cameras) if hasattr(dae, 'cameras') else 0
    n_mat = len(dae.materials) if hasattr(dae, 'materials') else 0
    print(f"Geometries: {n_geom}")
    print(f"Cameras: {n_cam}")
    print(f"Materials: {n_mat}")
    print("-" * 40)
    
    # Benchmark runs
    times = []
    for i in range(num_runs):
        start = time.perf_counter()
        collada.Collada(dae_path)
        end = time.perf_counter()
        times.append(end - start)
    
    times.sort()
    mean_time = sum(times) / len(times)
    median_time = times[len(times) // 2]
    
    print(f"Mean:   {mean_time * 1000:.1f} ms")
    print(f"Median: {median_time * 1000:.1f} ms")
    print(f"Min:    {min(times) * 1000:.1f} ms")
    print(f"Max:    {max(times) * 1000:.1f} ms")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark pycollada DAE loading",
    )
    parser.add_argument("dae_file", help="Path to DAE file to benchmark")
    parser.add_argument("--runs", "-n", type=int, default=10,
                        help="Number of benchmark runs (default: 10)")
    
    args = parser.parse_args()
    benchmark_load(args.dae_file, num_runs=args.runs)


if __name__ == "__main__":
    main()

