import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.simulation import Bus, BiddingCourier, ContractDispatcher, Order, simulate, scenario
from run_experiments import dataset, measure, POLICIES

class SystemTests(unittest.TestCase):
    def test_all_policies_complete_and_obey_capacity(self):
        for policy in POLICIES:
            for load in ('normal','overload'):
                r=simulate(load,policy,500)
                self.assertEqual(r['metrics']['delivered'],len(r['orders']))
                accepts=[m['payload']['id'] for m in r['trace'] if m['kind']=='ACCEPT']
                self.assertEqual(len(accepts),len(set(accepts)))
                for o in r['orders']:
                    self.assertLessEqual(o['weight'],r['profiles'][r['assignment'][o['id']]]['capacity'])

    def test_contract_and_central_same_route_objective(self):
        for seed in range(3):
            for load in ('sparse','stream','burst'):
                data=dataset(seed,load,3)
                a=simulate(load,'nearest',5000,data); b=simulate(load,'contract_net',5000,data)
                self.assertEqual(a['assignment'],b['assignment'])
                self.assertEqual(a['completed'],b['completed'])
                self.assertEqual(a['metrics']['travel'],b['metrics']['travel'])
                self.assertGreater(measure(b)['coordination'],measure(a)['coordination'])

    def test_bids_are_local_and_busy_or_overweight_refused(self):
        bus=Bus(); profiles={'c':dict(position=(0,0),capacity=2,speed=2)}
        d=ContractDispatcher(bus,profiles);c=BiddingCourier('c',bus,**profiles['c'])
        o=Order('x',0,(2,0),(4,0),2,10)
        d.bids['x']={};bus.send(0,'dispatcher','c','CFP',o.__dict__);bus.pump()
        self.assertEqual(d.bids['x']['c'],2)
        c.receive(dict(sender='dispatcher',kind='ASSIGN',time=0,payload=o.__dict__));bus.pump()
        bus.send(0,'dispatcher','c','CFP',dict(o.__dict__,id='y'));bus.pump()
        self.assertEqual(bus.trace[-1]['kind'],'REFUSE')
        c.state='idle';bus.send(0,'dispatcher','c','CFP',dict(o.__dict__,id='z',weight=3));bus.pump()
        self.assertEqual(bus.trace[-1]['kind'],'REFUSE')

    def test_zero_distance_and_future_arrival(self):
        for policy in POLICIES:
            data=({'c':dict(position=(0,0),capacity=1,speed=1)},[Order('x',7,(0,0),(0,0),1,10)])
            r=simulate('custom',policy,20,data)
            self.assertEqual(r['completed'],{'x':8})

    def test_impossible_order_does_not_block(self):
        for policy in POLICIES:
            r=simulate('capacity',policy,120)
            self.assertEqual(r['states']['HEAVY'],'waiting')
            self.assertEqual(r['metrics']['delivered'],6)

    def test_duplicate_assignment_and_causal_order(self):
        r=simulate('normal','contract_net')
        for o in r['orders']:
            kinds=[m['kind'] for m in r['trace'] if m['payload'].get('id')==o['id']]
            indexes=[kinds.index(k) for k in ('REQUEST','CFP','PROPOSE','ASSIGN','ACCEPT','PICKED_UP','DELIVERED')]
            self.assertEqual(indexes,sorted(indexes))
        bus=Bus(); d=ContractDispatcher(bus,{'c':dict(position=(0,0),capacity=2,speed=1)})
        c=BiddingCourier('c',bus,position=(0,0),capacity=2,speed=1)
        msg=dict(time=0,sender='dispatcher',kind='ASSIGN',payload=Order('x',0,(0,0),(1,0),1,10).__dict__)
        c.receive(msg);c.receive(msg)
        self.assertEqual(len([m for m in bus.trace if m['kind']=='ACCEPT']),1)

    def test_reproducible_inputs_and_paired_experiments(self):
        self.assertEqual(dataset(3,'stream',6),dataset(3,'stream',6))
        for policy in POLICIES:
            data=scenario('normal')
            self.assertEqual(simulate('normal',policy,120,data),simulate('normal',policy,120,data))

    def test_saved_results_are_complete_and_paired(self):
        import csv
        root=Path(__file__).resolve().parents[1]
        with (root/'results/runs.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),360)
        groups={}
        for r in rows:
            self.assertEqual(int(r['delivered']),60)
            groups.setdefault((r['load'],r['fleet'],r['seed']),[]).append(r)
        for group in groups.values():
            self.assertEqual(len(group),3)
            self.assertEqual(len(set(r['input_sha256'] for r in group)),1)
            a=next(r for r in group if r['policy']=='nearest')
            b=next(r for r in group if r['policy']=='contract_net')
            for m in ('makespan','mean_time','travel','late'):self.assertEqual(a[m],b[m])

if __name__=='__main__': unittest.main()
