import unittest
from simulation import simulate,SCENARIOS
class Tests(unittest.TestCase):
 def test_protected_completion(self):
  for s in range(20):
   for c in SCENARIOS:
    r=simulate(s,True,c);self.assertEqual(r['physical'],24);self.assertEqual(r['reported'],24);self.assertEqual(r['false_reports'],0)
 def test_loss_exposed(self):self.assertGreater(simulate(0,False,'lost_assign')['pending'],0)
 def test_forgery_exposed(self):self.assertGreater(simulate(0,False,'forged_done')['false_reports'],0)
 def test_replay_rejected(self):self.assertGreater(simulate(0,True,'stale_done')['rejected'],0)
 def test_reproducibility(self):self.assertEqual(simulate(5),simulate(5))
if __name__=='__main__':unittest.main()
