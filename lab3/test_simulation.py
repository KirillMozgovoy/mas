import unittest
from simulation import simulate
class Tests(unittest.TestCase):
 def test_collision_and_arbitration(self):
  self.assertEqual(simulate()['completed']>0,True)
  self.assertEqual(simulate(mode='uncoordinated')['completed'],0)
 def test_capacity(self):
  for mode in ('fifo','priority'):
   r=simulate(mode=mode);active=set()
   for m in r['trace']:
    if m['kind']=='RELEASE':active.remove(m['job'])
    if m['kind']=='GRANT':active.add(m['job'])
    self.assertLessEqual(len(active),1)
 def test_reproducibility(self):self.assertEqual(simulate(4),simulate(4))
 def test_progress(self):
  for mode in ('fifo','priority'):self.assertEqual(simulate(mode=mode,horizon=500)['completed'],60)
if __name__=='__main__':unittest.main()
