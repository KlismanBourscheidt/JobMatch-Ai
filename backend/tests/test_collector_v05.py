import unittest
from collector import role_ok, location_ok, analyze

class CollectorV05Tests(unittest.TestCase):
    def test_entry_role(self):
        self.assertTrue(role_ok("Estágio em Engenharia de Software"))
        self.assertTrue(role_ok("Junior Developer"))
        self.assertFalse(role_ok("Senior Developer"))
        self.assertFalse(role_ok("Sales Manager"))
    def test_location(self):
        self.assertTrue(location_ok("Curitiba, PR", ""))
        self.assertTrue(location_ok("Pinhais, PR", ""))
        self.assertTrue(location_ok("Remote, Brazil", ""))
        self.assertFalse(location_ok("Berlin, Germany", ""))
        self.assertFalse(location_ok("Brazil", "On-site"))
    def test_analysis(self):
        result = analyze({"description": "PHP, MySQL, Docker"})
        self.assertIn("php", result["matched_skills"])
        self.assertIn("docker", result["missing_skills"])
        self.assertGreaterEqual(result["score"], 50)

if __name__ == "__main__":
    unittest.main()
