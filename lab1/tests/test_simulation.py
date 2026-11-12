"""Protocol and domain invariants; run python -m unittest discover -s tests -v."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from simulation import Bus, Courier, Order, simulate


class SimulationTests(unittest.TestCase):
    def test_completion_capacity_and_unique_assignment(self):
        for policy in ('nearest', 'round_robin'):
            for name in ('normal', 'overload'):
                with self.subTest(policy=policy, name=name):
                    r = simulate(name, policy)
                    self.assertEqual(r['metrics']['pending'], 0)
                    self.assertTrue(all(s == 'delivered' for s in r['states'].values()))
                    accepts = [m for m in r['trace'] if m['kind'] == 'ACCEPT']
                    self.assertEqual(len(accepts), len(r['orders']))
                    self.assertEqual(len({m['payload']['id'] for m in accepts}), len(accepts))
                    for order in r['orders']:
                        cid = r['assignment'][order['id']]
                        self.assertLessEqual(order['weight'], r['profiles'][cid]['capacity'])
                        self.assertGreaterEqual(r['completed'][order['id']], order['release'])

    def test_impossible_order_waits_without_blocking_others(self):
        r = simulate('capacity', horizon=40)
        self.assertEqual(r['states']['HEAVY'], 'waiting')
        self.assertEqual(r['metrics']['delivered'], 6)
        self.assertNotIn('HEAVY', r['assignment'])

    def test_busy_and_overweight_rejected_and_duplicate_ignored(self):
        bus = Bus()
        c = Courier('c', bus, (0, 0), 3, 1)
        def offer(oid, weight):
            return dict(time=0, sender='dispatcher', kind='ASSIGN', payload=dict(
                id=oid, release=0, pickup=(0, 0), destination=(2, 0), weight=weight, deadline=10))
        c.receive(offer('heavy', 4))
        self.assertEqual(bus.trace[-1]['kind'], 'REJECT')
        c.receive(offer('one', 2))
        self.assertEqual(bus.trace[-1]['kind'], 'ACCEPT')
        count = len(bus.trace)
        c.receive(offer('one', 2))
        self.assertEqual(len(bus.trace), count)
        c.receive(offer('two', 1))
        self.assertEqual(bus.trace[-1]['kind'], 'REJECT')
        self.assertEqual(c.order.id, 'one')

    def test_zero_distance_and_future_release(self):
        custom = ({'c': dict(position=(0, 0), capacity=1, speed=1)},
                  [Order('zero', 5, (0, 0), (0, 0), 1, 6)])
        r = simulate(custom=custom)
        self.assertEqual(r['completed']['zero'], 6)
        self.assertEqual(r['metrics']['travel'], 0)

    def test_deterministic_and_causal_trace(self):
        r = simulate()
        self.assertEqual(r, simulate())
        times = [m['time'] for m in r['trace']]
        self.assertEqual(times, sorted(times))
        for order in r['orders']:
            stages = [m['kind'] for m in r['trace'] if m['payload'].get('id') == order['id']]
            self.assertEqual(stages, ['REQUEST', 'ASSIGN', 'ACCEPT', 'PICKED_UP', 'DELIVERED'])


if __name__ == '__main__':
    unittest.main()
