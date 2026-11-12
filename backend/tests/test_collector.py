import unittest
from collector import score_job, is_target_location
class CollectorTests(unittest.TestCase):
    def test_senior_excluded(self):
        self.assertEqual(score_job('Senior PHP Developer','PHP MySQL React','Curitiba'),0)
    def test_unrelated_title_excluded(self):
        self.assertEqual(score_job('Sales Representative','PHP MySQL','Curitiba'),0)
    def test_matching_skills(self):
        self.assertGreaterEqual(score_job('Estágio Desenvolvedor','PHP MySQL JavaScript HTML CSS Git','Curitiba'),80)
    def test_location(self):
        self.assertFalse(is_target_location('Berlin','On-site in Germany'))
if __name__=='__main__':unittest.main()
