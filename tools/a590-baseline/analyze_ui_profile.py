"""Read exported camera CSV without rewriting originals; no automatic leak verdict."""
import argparse
import csv
import json
import math
from pathlib import Path


def read(path):
    with path.open(encoding='ascii') as stream:
        return list(csv.DictReader(line for line in stream if not line.startswith('#')))


def summarize(folder):
    stats = read(folder / 'UISTAT.CSV')
    memory = read(folder / 'UIMEM.CSV')
    delays = sorted(int(r['response_ms']) for r in read(folder / 'UIDELAY.CSV'))
    events = ['init', 'draw', 'move', 'response', 'save', 'module_load', 'module_unload']
    result = {'events': {}, 'response_samples': len(delays), 'memory': memory,
              'limits': 'First 64 coalesced dispatch-to-draw samples; tick resolution and instrumentation overhead apply. No leak diagnosis.'}
    for row in stats:
        count = int(row['count'])
        result['events'][events[int(row['event'])]] = {
            'count': count, 'mean_ms': int(row['total_ms']) / count if count else None,
            'max_ms': int(row['max_ms']), 'last_ms': int(row['last_ms'])}
    for percentile in (50, 95):
        result[f'response_p{percentile}_ms_nearest_rank'] = (
            delays[math.ceil(len(delays) * percentile / 100) - 1] if delays else None)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='directory containing all three camera CSV files')
    args = parser.parse_args()
    print(json.dumps(summarize(args.folder), ensure_ascii=False, indent=2))
