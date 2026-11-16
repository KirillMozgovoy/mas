"""Reproduce 360 paired runs and nine full demonstration traces; stdlib only."""
import gzip
import csv
import hashlib
import json
import random
import statistics
from pathlib import Path
from src.simulation import Order, simulate

ROOT = Path(__file__).resolve().parent
POLICIES = ('round_robin', 'nearest', 'contract_net')
LOADS = {'sparse': 4, 'stream': 1, 'burst': 0}
COORDINATION = {'CFP', 'PROPOSE', 'REFUSE', 'NOT_SELECTED', 'ASSIGN', 'ACCEPT', 'REJECT'}


def dataset(seed, load, fleet):
    rng = random.Random(seed)
    profiles = {f'courier_{i+1}': dict(position=(rng.randrange(20), rng.randrange(20)),
                  capacity=(3, 6, 4)[i % 3], speed=(1, 1, 2)[i % 3]) for i in range(fleet)}
    orders = [Order(f'O{i:03}', i * LOADS[load],
                    (rng.randrange(20), rng.randrange(20)),
                    (rng.randrange(20), rng.randrange(20)),
                    rng.randint(1, 6), i * LOADS[load] + 35) for i in range(60)]
    return profiles, orders


def measure(r):
    durations = sorted(r['completed'][o['id']] - o['release'] for o in r['orders']
                       if o['id'] in r['completed'])
    coordination = [m for m in r['trace'] if m['kind'] in COORDINATION]
    counts = [sum(c == cid for c in r['assignment'].values()) for cid in r['profiles']]
    return dict(makespan=r['elapsed'], mean_time=r['metrics']['mean_delivery_time'],
                p95=durations[max(0, (95 * len(durations) + 99)//100 - 1)] if durations else None,
                late=r['metrics']['late'], delivered=r['metrics']['delivered'],
                travel=r['metrics']['travel'], messages=len(r['trace']),
                coordination=len(coordination),
                coordination_bytes=sum(len(json.dumps(m, ensure_ascii=False, separators=(',', ':')).encode()) for m in coordination),
                assignment_cv=statistics.pstdev(counts)/statistics.mean(counts) if sum(counts) else 0)


def main():
    (ROOT/'results').mkdir(exist_ok=True); (ROOT/'demo').mkdir(exist_ok=True)
    rows, examples, inputs = [], [], []
    for load in LOADS:
        for fleet in (3, 6):
            for seed in range(20):
                profiles, orders = dataset(seed, load, fleet)
                from dataclasses import asdict
                source = dict(load=load, fleet=fleet, seed=seed, profiles=profiles,
                              orders=[asdict(o) for o in orders])
                digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
                inputs.append(dict(**source, input_sha256=digest))
                for policy in POLICIES:
                    r = simulate(load, policy, 5000, (profiles, orders))
                    if r['metrics']['delivered'] != len(orders):
                        raise RuntimeError('Incomplete experiment')
                    rows.append(dict(load=load, fleet=fleet, seed=seed, policy=policy,
                                     input_sha256=digest, **measure(r)))
                    if fleet == 3 and seed == 0:
                        examples.append(r)
    with (ROOT/'results/runs.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    metrics = list(measure(examples[0]))
    summary=[]
    for load in LOADS:
        for fleet in (3,6):
            for policy in POLICIES:
                group=[r for r in rows if (r['load'],r['fleet'],r['policy'])==(load,fleet,policy)]
                item=dict(load=load,fleet=fleet,policy=policy,n=len(group))
                for m in metrics:
                    values=[r[m] for r in group]; se=statistics.stdev(values)/(len(values)**.5)
                    item[m]=dict(mean=statistics.mean(values),sd=statistics.stdev(values),ci95=2.093*se)
                summary.append(item)
    (ROOT/'results/inputs.json.gz').write_bytes(gzip.compress(json.dumps(inputs,ensure_ascii=False,indent=2).encode(),mtime=0))
    (ROOT/'results/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    (ROOT/'demo/traces.json').write_text(json.dumps(examples,ensure_ascii=False,separators=(',',':')))
    print(f'{len(rows)} runs, {len(inputs)} input sets, {len(examples)} traces')
    for item in summary:
        print(item['load'],item['fleet'],item['policy'],
              {m:round(item[m]['mean'],2) for m in ('makespan','mean_time','late','coordination')})

if __name__=='__main__': main()
