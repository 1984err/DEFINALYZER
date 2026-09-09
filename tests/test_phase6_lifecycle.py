import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from definalyzer.process_runner import run_provider_process
from definalyzer.dashboard import DashboardJobManager
from definalyzer.application import DefinalyzerApplication
from definalyzer.workspace import WorkspaceManager


class LifecycleTests(unittest.TestCase):
    def test_checkpoint_replace_retries_a_transient_windows_reader_lock(self):
        from definalyzer.research_scope import _write
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json';path.write_text('previous')
            replace=Path.replace;attempts=[]
            def transient(source,target):
                attempts.append(source)
                if len(attempts)<3:
                    error=PermissionError('reader holds file');error.winerror=5;raise error
                return replace(source,target)
            with patch.object(Path,'replace',transient),patch('definalyzer.research_scope.time.sleep'):
                _write(path,'complete checkpoint')
            self.assertEqual(path.read_text(),'complete checkpoint')
            self.assertEqual(len(attempts),3)

    def test_checkpoint_permanent_replace_failure_keeps_previous_version(self):
        from definalyzer.research_scope import _write
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state.json';path.write_text('previous')
            error=PermissionError('locked');error.winerror=5
            with patch.object(Path,'replace',side_effect=error) as replace,patch('definalyzer.research_scope.time.sleep'):
                with self.assertRaises(PermissionError):_write(path,'replacement')
            self.assertEqual(replace.call_count,6)
            self.assertEqual(path.read_text(),'previous')

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object containment')
    def test_hard_killed_provider_owner_does_not_leave_a_child_running(self):
        with tempfile.TemporaryDirectory() as directory:
            heartbeat=Path(directory)/'alive.txt'
            child="import time,pathlib; p=pathlib.Path("+repr(str(heartbeat))+");\nwhile True:\n p.write_text(str(time.monotonic()))\n time.sleep(.05)"
            owner="from definalyzer.process_runner import run_provider_process; import sys; run_provider_process([sys.executable,'-c',"+repr(child)+"],timeout=30,text=True)"
            process=subprocess.Popen([sys.executable,'-c',owner],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for _ in range(100):
                    if heartbeat.exists():break
                    time.sleep(.05)
                self.assertTrue(heartbeat.exists())
            finally:
                process.kill();process.communicate(timeout=5)
            time.sleep(.1)
            before=heartbeat.read_text()
            time.sleep(.2)
            self.assertEqual(heartbeat.read_text(),before)

    def test_provider_timeout_stops_descendant_that_keeps_stdout_open(self):
        with tempfile.TemporaryDirectory() as directory:
            heartbeat=Path(directory)/'heartbeat.txt'
            child="import time,pathlib; p=pathlib.Path("+repr(str(heartbeat))+");\nwhile True:\n p.write_text(str(time.monotonic()))\n time.sleep(.05)"
            parent="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',"+repr(child)+"]); time.sleep(30)"
            started=time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                run_provider_process([sys.executable,'-c',parent],timeout=1,text=True,encoding='utf-8')
            self.assertLess(time.monotonic()-started,5)
            self.assertTrue(heartbeat.exists())
            before=heartbeat.read_text()
            time.sleep(.2)
            self.assertEqual(heartbeat.read_text(),before)

    def test_provider_returns_response_and_exit_code(self):
        result=run_provider_process([sys.executable,'-c',"print('finished')"],timeout=5,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout.strip(),'finished')

    def test_jobs_record_nonzero_and_semantic_failures_as_needing_attention(self):
        for result in ({'exit_code':2},{'status':'needs_attention','message':'Missing support'}):
            with self.subTest(result=result),tempfile.TemporaryDirectory() as directory:
                manager=WorkspaceManager(Path(directory)/'output');manager.initialize()
                jobs=DashboardJobManager(DefinalyzerApplication(manager))
                try:
                    with patch('definalyzer.dashboard._execute_job',return_value=result):
                        job=jobs.submit(action='provider-test',project=None,payload={})
                        for _ in range(100):
                            saved=jobs.get(job['job_id'])
                            if saved['status'] not in {'running','queued'}:break
                            time.sleep(.01)
                        self.assertEqual(saved['status'],'needs_attention')
                        self.assertEqual(saved['result'],result)
                        self.assertIsNotNone(saved['finished_at'])
                finally:jobs.close()

    def test_interruption_is_terminal_without_restarting_the_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=WorkspaceManager(Path(directory)/'output');manager.initialize()
            jobs=DashboardJobManager(DefinalyzerApplication(manager))
            try:
                with patch('definalyzer.dashboard._execute_job',side_effect=KeyboardInterrupt()):
                    job=jobs.submit(action='provider-test',project=None,payload={})
                    for _ in range(100):
                        saved=jobs.get(job['job_id'])
                        if saved['status'] not in {'running','queued'}:break
                        time.sleep(.01)
                    self.assertEqual(saved['status'],'interrupted')
                    self.assertIsNotNone(saved['finished_at'])
            finally:jobs.close()
