import json
import sys
import tempfile
import unittest
from pathlib import Path

from covdiff_lite.process import CommandRunner, StageError


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runner = CommandRunner(self.root)

    def test_expected_nonzero_program_exit_is_valid(self):
        result = self.runner.run('execute', [sys.executable, '-c', 'print("witness"); raise SystemExit(7)'],
                                 2, expected_exit=7)
        self.assertEqual(result, 'witness\n')
        self.assertEqual(json.loads((self.root / 'commands.json').read_text())[0]['exit_code'], 7)

    def test_failed_command_retains_stderr(self):
        with self.assertRaises(StageError):
            self.runner.run('compile', [sys.executable, '-c', 'import sys; print("broken", file=sys.stderr); sys.exit(1)'], 2)
        self.assertEqual((self.root / 'compile.stderr').read_text(), 'broken\n')

    def test_timeout_retains_output_and_marks_stage(self):
        with self.assertRaises(StageError) as raised:
            self.runner.run('execute', [sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(10)'], 0.2)
        self.assertEqual(raised.exception.stage, 'execute')
        self.assertTrue(self.runner.records[0]['timed_out'])
        self.assertEqual((self.root / 'execute.stdout').read_text(), 'started\n')
