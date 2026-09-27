import unittest
from reconcile_inventory import normalized_title


class TitleNormalizationTests(unittest.TestCase):
    def test_escaped_markup_is_not_title_text(self):
        plain = 'Cell invasion in C. elegans.'
        for markup in ['<i>C. elegans</i>', '&lt;i&gt;C. elegans&lt;/i&gt;', '&amp;lt;i&amp;gt;C. elegans&amp;lt;/i&amp;gt;']:
            self.assertEqual(normalized_title(plain), normalized_title('Cell invasion in ' + markup))

    def test_not_fuzzy(self):
        self.assertNotEqual(normalized_title('Adaptation in mice'), normalized_title('Adaptation in rats'))


if __name__ == '__main__':
    unittest.main()
