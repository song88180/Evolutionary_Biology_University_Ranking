import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study_config import load_openalex_key, openalex_headers, screening_key


class ScreeningIdentifierTests(unittest.TestCase):
    def test_source_id_is_not_fabricated_doi(self):
        self.assertEqual(screening_key('PMC:PMC12345'), 'PMC:PMC12345')

    def test_legacy_nature_id(self):
        self.assertEqual(screening_key('s41586-026-12345-6'), '10.1038/s41586-026-12345-6')

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            screening_key('')


class CredentialTests(unittest.TestCase):
    def test_environment_value_has_precedence(self):
        with patch.dict(os.environ, {"OPENALEX_API_KEY": "fixture-env"}):
            self.assertEqual(load_openalex_key('/not/a/file'), 'fixture-env')
            self.assertEqual(openalex_headers(), {"Authorization": "Bearer fixture-env"})

    def test_dotenv_quoting_and_comments(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            path.write_text('IGNORED=x\nexport OPENALEX_API_KEY="fixture-value" # comment\n')
            self.assertEqual(load_openalex_key(path), 'fixture-value')
            self.assertNotIn('IGNORED', os.environ)

    def test_shell_syntax_is_not_executed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            path.write_text("OPENALEX_API_KEY='$(never_execute_this)'\n")
            self.assertEqual(load_openalex_key(path), '$(never_execute_this)')

    def test_invalid_quoting_has_sanitized_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            path.write_text('OPENALEX_API_KEY="fixture-secret\n')
            with self.assertRaises(ValueError) as result:
                load_openalex_key(path)
            self.assertNotIn('fixture-secret', str(result.exception))


if __name__ == '__main__':
    unittest.main()
