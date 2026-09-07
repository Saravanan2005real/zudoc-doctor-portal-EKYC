import unittest
from .matcher import normalize_name, calculate_name_match_percentage

class TestMatcher(unittest.TestCase):
    def test_name_normalization(self):
        tests = [
            ("Dr. Rahul Kumar", "rahul kumar"),
            ("Dr.  Rahul   Kumar", "rahul kumar"),
            ("Doctor Rahul Kumar, M.D.", "rahul kumar m d"),
            ("Prof. Rahul Kumar", "rahul kumar"),
        ]

        for input_name, expected in tests:
            actual = normalize_name(input_name)
            self.assertEqual(actual, expected, f"normalize_name('{input_name}') = '{actual}', expected '{expected}'")

    def test_jaro_winkler_fuzzy_matching(self):
        tests = [
            ("Dr. Rahul Kumar", "Rahul Kumar", 100.0),
            ("Dr. Rahul Kumar", "Rahul K.", 88.0),
            ("Rahul Kumar", "rahul kumar", 100.0),
            ("Rahul Kumar", "Sunil Sharma", 0.0),
        ]

        for name1, name2, min_score in tests:
            score = calculate_name_match_percentage(name1, name2)
            self.assertGreaterEqual(score, min_score, f"calculate_name_match_percentage('{name1}', '{name2}') = {score:.2f}, expected at least {min_score:.2f}")

if __name__ == '__main__':
    unittest.main()
