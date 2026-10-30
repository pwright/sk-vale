import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name('leben.py')


class HeadingFlatteningTests(unittest.TestCase):
    def test_thresholds_preserve_boundaries_and_assembly_content(self):
        for threshold in [None, 2, 3, 4, 5, 6]:
            with self.subTest(threshold=threshold), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / 'input.adoc'
                source.write_text(
                    '[[guide]]\n= Guide\n\n=== Introduction\n\nIntro.\n\n'
                    '[id="topic"]\n==== Topic\n\nBody.\n\n'
                    + ''.join(
                        f'{"=" * level} Heading {level}\n\nText.\n\n'
                        f'{"=" * level} Table {level}\n\n|===\n|Cell\n|===\n\n'
                        for level in range(2, 7)
                    )
                    + '====\nExample content.\n====\n\n'
                    '[[next]]\n== Next\n\nNext body.\n'
                )
                command = [sys.executable, str(SCRIPT), str(source)]
                if threshold is not None:
                    command.extend(['--flatten-from-level', str(threshold)])
                result = subprocess.run(command, cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                module = (root / 'modules/topic.adoc').read_text()
                assembly = (root / 'assemblies/assembly-guide.adoc').read_text()
                self.assertIn('= Topic\n', module)
                self.assertIn('=== Introduction\n', assembly)
                self.assertIn('include::../modules/topic.adoc[leveloffset=+3]', assembly)
                self.assertIn('include::../modules/next.adoc[leveloffset=+1]', assembly)
                self.assertEqual(len(list((root / 'modules').glob('*.adoc'))), 2)
                self.assertIn('====\nExample content.\n====\n', module)
                for level in range(2, 7):
                    if level >= (threshold if threshold is not None else 3):
                        self.assertIn(f'**Heading {level}**\n', module)
                        self.assertIn(f'.Table {level}\n|===', module)
                        self.assertNotIn(f'{"=" * level} Heading {level}\n', module)
                    else:
                        self.assertIn(f'{"=" * level} Heading {level}\n', module)
                        self.assertIn(f'{"=" * level} Table {level}\n', module)

    def test_invalid_thresholds_fail_before_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            for value in ['1', '7', 'three']:
                with self.subTest(value=value):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), 'missing.adoc', '--flatten-from-level', value],
                        cwd=tmp, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn('--flatten-from-level', result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
