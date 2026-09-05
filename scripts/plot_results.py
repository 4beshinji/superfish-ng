# SPDX-License-Identifier: Apache-2.0
"""Render a saved mode, electric arrows, and axial/radial field probes."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from superfish_ng.visualize import plot_mode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--mode', type=int, default=1, help='one-based mode number')
    parser.add_argument('--probe-z-m', type=float, help='radial probe z coordinate in metres')
    parser.add_argument('--mesh', action='store_true')
    args = parser.parse_args()
    try:
        plot_mode(args.run, args.out, args.mode, args.probe_z_m, args.mesh)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
