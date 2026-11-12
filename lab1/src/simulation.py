"""Discrete-time courier MAS, Python 3.10+, standard library only.

Run: python src/simulation.py --scenario normal --output demo/normal.json
The bus delivers FIFO messages; agents do not directly mutate each other.
"""
from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Order:
    id: str
    release: int
    pickup: tuple[int, int]
    destination: tuple[int, int]
    weight: int
    deadline: int


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Bus:
    def __init__(self):
        self.agents = {}
        self.queue = deque()
        self.trace = []

    def register(self, agent):
        if agent.id in self.agents:
            raise ValueError("Duplicate agent ID")
        self.agents[agent.id] = agent

    def send(self, time, sender, receiver, kind, payload):
        message = dict(time=time, sender=sender, receiver=receiver,
                       kind=kind, payload=payload.copy())
        self.queue.append(message)
        self.trace.append(message)

    def pump(self):
        delivered = 0
        while self.queue:
            message = self.queue.popleft()
            self.agents[message['receiver']].receive(message)
            delivered += 1
            if delivered > 10000:
                raise RuntimeError("Message cycle")


class Source:
    id = 'source'

    def __init__(self, bus, orders):
        self.bus, self.orders = bus, orders
        bus.register(self)

    def tick(self, time):
        for order in self.orders:
            if order.release == time:
                self.bus.send(time, self.id, 'dispatcher', 'REQUEST', asdict(order))

    def receive(self, message):
        raise ValueError("Source has no incoming protocol messages")


class Dispatcher:
    id = 'dispatcher'

    def __init__(self, bus, profiles, policy='nearest'):
        self.bus, self.profiles, self.policy = bus, profiles, policy
        self.orders, self.states, self.assignment = {}, {}, {}
        self.status = {cid: dict(position=list(p['position']), idle=True)
                       for cid, p in profiles.items()}
        self.completed, self.pending = {}, {}
        self.round_robin_cursor = 0
        bus.register(self)

    def receive(self, message):
        p, kind, sender = message['payload'], message['kind'], message['sender']
        oid = p.get('id')
        if kind == 'REQUEST' and sender == 'source':
            if oid not in self.orders:
                self.orders[oid] = Order(**p)
                self.states[oid] = 'waiting'
        elif kind in ('ACCEPT', 'REJECT'):
            if self.pending.get(oid) != sender:
                return  # stale or duplicate reply
            del self.pending[oid]
            if kind == 'ACCEPT':
                self.states[oid] = 'assigned'
                self.assignment[oid] = sender
            else:
                self.states[oid] = 'waiting'
                self.status[sender] = dict(position=p['position'], idle=p['idle'])
        elif kind == 'PICKED_UP' and self.assignment.get(oid) == sender:
            if self.states[oid] == 'assigned':
                self.states[oid] = 'in_transit'
        elif kind == 'DELIVERED' and self.assignment.get(oid) == sender:
            if self.states[oid] == 'in_transit':
                self.states[oid] = 'delivered'
                self.completed[oid] = message['time']
        elif kind == 'STATUS' and sender in self.profiles:
            self.status[sender] = dict(position=p['position'], idle=p['idle'])

    def tick(self, time):
        # Order queue: earliest release first, then ID. Deadline is a metric,
        # not a scheduling priority in lab 1.
        for order in sorted(self.orders.values(), key=lambda o: (o.release, o.id)):
            if self.states[order.id] != 'waiting':
                continue
            eligible = [cid for cid, p in self.profiles.items()
                        if self.status[cid]['idle'] and p['capacity'] >= order.weight]
            if not eligible:
                continue
            if self.policy == 'nearest':
                cid = min(eligible, key=lambda c: (
                    (distance(self.status[c]['position'], order.pickup) +
                     distance(order.pickup, order.destination)) / self.profiles[c]['speed'], c))
            else:
                ids = sorted(self.profiles)
                cid = next(ids[(self.round_robin_cursor + j) % len(ids)]
                           for j in range(len(ids))
                           if ids[(self.round_robin_cursor + j) % len(ids)] in eligible)
                self.round_robin_cursor = (ids.index(cid) + 1) % len(ids)
            self.status[cid]['idle'] = False  # reservation before sending
            self.states[order.id] = 'offered'
            self.pending[order.id] = cid
            self.bus.send(time, self.id, cid, 'ASSIGN', asdict(order))


class Courier:
    def __init__(self, cid, bus, position, capacity, speed):
        self.id, self.bus = cid, bus
        self.position = list(position)
        self.capacity, self.speed = capacity, speed
        self.state, self.order = 'idle', None
        self.travel = 0
        self.seen = set()
        bus.register(self)

    def receive(self, message):
        if message['kind'] != 'ASSIGN' or message['sender'] != 'dispatcher':
            return
        order = Order(**message['payload'])
        if order.id in self.seen:
            return  # repeated ASSIGN must not trigger a second execution
        if self.state != 'idle' or order.weight > self.capacity:
            self.bus.send(message['time'], self.id, 'dispatcher', 'REJECT',
                          dict(id=order.id, position=self.position.copy(),
                               idle=self.state == 'idle'))
            return
        self.order, self.state = order, 'to_pickup'
        self.seen.add(order.id)
        self.bus.send(message['time'], self.id, 'dispatcher', 'ACCEPT', dict(id=order.id))

    def tick(self, time):
        if self.state == 'idle':
            return
        # Move on x first, then y. A tick lasts one time unit, and delivery
        # events are recorded at its end (time + 1). Zero-distance legs are legal.
        budget = self.speed
        while self.state != 'idle':
            target = (self.order.pickup if self.state == 'to_pickup'
                      else self.order.destination)
            if self.position != list(target):
                if budget == 0:
                    break
                axis = 0 if self.position[0] != target[0] else 1
                step = min(budget, abs(target[axis] - self.position[axis]))
                self.position[axis] += step if target[axis] > self.position[axis] else -step
                self.travel += step
                budget -= step
                continue
            if self.state == 'to_pickup':
                self.state = 'to_destination'
                self.bus.send(time + 1, self.id, 'dispatcher', 'PICKED_UP',
                              dict(id=self.order.id))
            else:
                self.bus.send(time + 1, self.id, 'dispatcher', 'DELIVERED',
                              dict(id=self.order.id))
                self.state, self.order = 'idle', None
        self.bus.send(time + 1, self.id, 'dispatcher', 'STATUS',
                      dict(position=self.position.copy(), idle=self.state == 'idle'))


def scenario(name):
    profiles = {
        'courier_1': dict(position=(0, 0), capacity=3, speed=1),
        'courier_2': dict(position=(8, 0), capacity=6, speed=1),
        'courier_3': dict(position=(4, 8), capacity=4, speed=2),
    }
    orders = [
        Order('O1', 0, (1, 0), (3, 2), 2, 8),
        Order('O2', 0, (7, 0), (7, 4), 5, 10),
        Order('O3', 1, (4, 7), (2, 6), 3, 7),
        Order('O4', 2, (0, 1), (1, 5), 2, 14),
        Order('O5', 3, (6, 6), (8, 8), 4, 16),
        Order('O6', 4, (3, 3), (5, 1), 1, 13),
    ]
    if name == 'overload':
        orders = [Order(f'O{i+1:02}', 0, (i % 9, i * 2 % 9),
                        ((i + 4) % 9, (i * 3 + 1) % 9), 1 + i % 6, 10)
                  for i in range(18)]
    elif name == 'capacity':
        orders += [Order('HEAVY', 0, (0, 0), (1, 1), 9, 20)]
    elif name != 'normal':
        raise ValueError(name)
    return profiles, orders


def simulate(name='normal', policy='nearest', horizon=120, custom=None):
    if horizon < 1 or policy not in ('nearest', 'round_robin'):
        raise ValueError('Invalid simulation configuration')
    profiles, orders = custom if custom is not None else scenario(name)
    bus = Bus()
    source = Source(bus, orders)
    dispatcher = Dispatcher(bus, profiles, policy)
    couriers = [Courier(cid, bus, **p) for cid, p in profiles.items()]
    elapsed = 0
    for time in range(horizon):
        source.tick(time)
        bus.pump()
        dispatcher.tick(time)
        bus.pump()
        for courier in couriers:
            courier.tick(time)
        bus.pump()
        elapsed = time + 1
        # Stop when every input order is delivered, including future arrivals.
        if len(dispatcher.completed) == len(orders):
            break
    delivered = len(dispatcher.completed)
    duration = [t - dispatcher.orders[oid].release for oid, t in dispatcher.completed.items()]
    late = sum(t > dispatcher.orders[oid].deadline for oid, t in dispatcher.completed.items())
    return dict(
        scenario=name, policy=policy, horizon=horizon, elapsed=elapsed,
        profiles=profiles, orders=[asdict(o) for o in orders],
        states={o.id: dispatcher.states.get(o.id, 'not_released') for o in orders},
        assignment=dispatcher.assignment, completed=dispatcher.completed,
        metrics=dict(total=len(orders), delivered=delivered, pending=len(orders)-delivered,
                     late=late, mean_delivery_time=round(sum(duration)/delivered, 3) if delivered else None,
                     messages=len(bus.trace), travel=sum(c.travel for c in couriers)),
        couriers=[dict(id=c.id, position=c.position, state=c.state,
                       travel=c.travel, capacity=c.capacity, speed=c.speed) for c in couriers],
        trace=bus.trace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['normal', 'overload', 'capacity'], default='normal')
    parser.add_argument('--policy', choices=['nearest', 'round_robin'], default='nearest')
    parser.add_argument('--horizon', type=int, default=120)
    parser.add_argument('--output', type=Path, default=Path('demo/normal.json'))
    args = parser.parse_args()
    result = simulate(args.scenario, args.policy, args.horizon)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result['metrics'], ensure_ascii=False, indent=2))
    print('Trace:', args.output)


if __name__ == '__main__':
    main()
