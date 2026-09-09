#!/usr/bin/env python3
"""Push a run's latency/trajectory CSVs (written by latency_logger.py and
trajectory_logger.py, unmodified) into InfluxDB as line protocol, so Grafana
can chart them. Used by digital_twins/f1tenth/lifecycle/save.

Uses only the standard library (urllib) so it needs no extra dependency
inside the f1tenth-dt image.

Usage:
    python3 csv_to_influx.py <run_data_dir> --run <run_label>

<run_data_dir> is expected to contain latency/*.csv and/or trajectory/*.csv,
matching the --output-dir layout produced by dtaas/.../f1tenth_dt.launch.py.
"""
import argparse
import csv
import pathlib
import sys
import urllib.error
import urllib.request


def escape_tag(value: str) -> str:
    return str(value).replace(' ', '\\ ').replace(',', '\\,').replace('=', '\\=')


def latency_lines(csv_path: pathlib.Path, run_label: str):
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            yield (
                f"latency,run={escape_tag(run_label)} "
                f"seq={row['seq']}i,"
                f"one_way_ms={row['one_way_ms']},"
                f"steering_angle={row['steering_angle']},"
                f"speed={row['speed']} "
                f"{row['recv_time_ns']}"
            )


def trajectory_lines(csv_path: pathlib.Path, run_label: str):
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            yield (
                f"trajectory,run={escape_tag(run_label)},"
                f"source={escape_tag(row['source'])} "
                f"x={row['x']},"
                f"y={row['y']},"
                f"heading_rad={row['heading_rad']},"
                f"speed_mps={row['speed_mps']} "
                f"{row['timestamp_ns']}"
            )


def write_batch(lines, url, org, bucket, token):
    if not lines:
        return
    body = ('\n'.join(lines) + '\n').encode('utf-8')
    endpoint = f"{url}/api/v2/write?org={org}&bucket={bucket}&precision=ns"
    req = urllib.request.Request(
        endpoint, data=body, method='POST',
        headers={
            'Authorization': f'Token {token}',
            'Content-Type': 'text/plain; charset=utf-8',
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        sys.exit(f"InfluxDB write failed ({exc.code}): {exc.read().decode()}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach InfluxDB at {url}: {exc.reason}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data_dir', type=pathlib.Path)
    parser.add_argument('--run', required=True, help='Run label / tag value')
    parser.add_argument('--influx-url', default='http://influxdb:8086')
    parser.add_argument('--org', default='f1tenth')
    parser.add_argument('--bucket', default='f1tenth_dt')
    parser.add_argument('--token', default='f1tenth-local-dev-token')
    args = parser.parse_args()

    lines = []
    latency_dir = args.data_dir / 'latency'
    trajectory_dir = args.data_dir / 'trajectory'

    for csv_path in sorted(latency_dir.glob('*.csv')) if latency_dir.exists() else []:
        lines.extend(latency_lines(csv_path, args.run))

    for csv_path in sorted(trajectory_dir.glob('*.csv')) if trajectory_dir.exists() else []:
        lines.extend(trajectory_lines(csv_path, args.run))

    if not lines:
        print(f"No CSVs found under {args.data_dir} (latency/ or trajectory/)")
        return

    # InfluxDB caps request body size; batch defensively.
    batch_size = 5000
    for i in range(0, len(lines), batch_size):
        write_batch(lines[i:i + batch_size], args.influx_url, args.org,
                    args.bucket, args.token)

    print(f"Wrote {len(lines)} points to {args.bucket} (run={args.run})")


if __name__ == '__main__':
    main()
