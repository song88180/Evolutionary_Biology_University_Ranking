import unittest
from fractions import Fraction
from export_reviewed import distribute, university_matches


class CreditTests(unittest.TestCase):
    def test_duplicate_institutions_and_outside_pool_keep_equal_shares(self):
        result = distribute("17.1", ["university-a", "university-a", "outside:b", "university-c"])
        self.assertEqual(len(result), 3)
        self.assertEqual(result["university-a"], Fraction("5.7"))
        self.assertEqual(sum(result.values(), Fraction()), Fraction("17.1"))

    def test_nested_names_do_not_create_spurious_university(self):
        needles = {"china agricultural university": "cau", "south china agricultural university": "scau"}
        self.assertEqual(university_matches("College, South China Agricultural University, Guangzhou", needles), {"scau"})
        self.assertEqual(university_matches("South China Agricultural University and China Agricultural University", needles), {"scau", "cau"})


if __name__ == "__main__":
    unittest.main()
