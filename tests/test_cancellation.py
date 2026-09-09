import asyncio
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from definalyzer.cancellation import cancellation_scope, check_cancelled, cancellable, OperationCancelled
from definalyzer.dashboard import DashboardJobManager, create_dashboard_server
from definalyzer.application import DefinalyzerApplication
from definalyzer.workspace import WorkspaceManager
from definalyzer.process_runner import run_provider_process


class CancellationTests(unittest.TestCase):
    def test_second_dashboard_cannot_take_over_a_live_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=WorkspaceManager(Path(directory)/'output')
            first=create_dashboard_server(manager,port=0)
            try:
                with self.assertRaisesRegex(RuntimeError,'already running'):
                    create_dashboard_server(manager,port=0)
            finally:first.server_close()
            reopened=create_dashboard_server(manager,port=0)
            reopened.server_close()

    def test_stop_kills_provider_tree_skips_queued_job_and_preserves_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); manager=WorkspaceManager(root/'output');manager.initialize()
            jobs=DashboardJobManager(DefinalyzerApplication(manager));calls=[]
            heartbeat=root/'heartbeat'; checkpoint=root/'saved'
            child='import time,pathlib; p=pathlib.Path('+repr(str(heartbeat))+');\nwhile True:\n p.write_text(str(time.monotonic()))\n time.sleep(.05)'
            parent='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); time.sleep(60)'
            def execute(*args,**kwargs):
                calls.append(kwargs['payload'])
                if kwargs['payload'].get('short'):return {'exit_code':0}
                checkpoint.write_text('completed work')
                run_provider_process([sys.executable,'-c',parent],timeout=60,text=True)
                self.fail('Cancelled provider returned as successful')
            try:
                with patch('definalyzer.dashboard._execute_job',side_effect=execute):
                    job=jobs.submit(action='provider-test',project='test',payload={})
                    for _ in range(150):
                        if heartbeat.exists():break
                        time.sleep(.02)
                    self.assertTrue(heartbeat.exists())
                    queued=jobs.submit(action='provider-test',project=None,payload={'queued':True})
                    self.assertEqual(jobs.cancel(queued['job_id'])['status'],'cancelled')
                    self.assertEqual(jobs.cancel(job['job_id'])['status'],'stopping')
                    for _ in range(150):
                        stopped=jobs.get(job['job_id'])
                        if stopped['status']=='cancelled':break
                        time.sleep(.02)
                    self.assertEqual(stopped['status'],'cancelled')
                    self.assertFalse(jobs.has_active('test'))
                    self.assertEqual(checkpoint.read_text(),'completed work')
                    before=heartbeat.read_bytes();time.sleep(.2)
                    self.assertEqual(heartbeat.read_bytes(),before)
                    self.assertEqual(jobs.cancel(job['job_id'])['finished_at'],stopped['finished_at'])
                    later=jobs.submit(action='provider-test',project=None,payload={'short':True})
                    for _ in range(100):
                        if jobs.get(later['job_id'])['status']=='complete':break
                        time.sleep(.01)
                    self.assertEqual(jobs.get(later['job_id'])['status'],'complete')
                    self.assertEqual(calls,[{}, {'short':True}])
                saved=json.loads((manager.root/'dashboard-jobs.json').read_text())
                self.assertEqual(next(r for r in saved['jobs'] if r['job_id']==job['job_id'])['status'],'cancelled')
            finally:jobs.close()

    def test_cancelled_scope_never_launches_provider(self):
        event=threading.Event();event.set()
        with patch('definalyzer.process_runner.subprocess.Popen') as launch:
            with self.assertRaises(OperationCancelled),cancellation_scope(event):
                run_provider_process([sys.executable,'-c','pass'],timeout=1)
            launch.assert_not_called()

    def test_async_cancellation_runs_cleanup(self):
        event=threading.Event();cleaned=[]
        async def operation():
            try:await asyncio.sleep(30)
            finally:cleaned.append(True)
        timer=threading.Timer(.1,event.set);timer.start()
        try:
            with self.assertRaises(OperationCancelled),cancellation_scope(event):
                asyncio.run(cancellable(operation()))
            self.assertEqual(cleaned,[True])
        finally:timer.cancel()

    def test_cancel_during_rate_limit_wait_prevents_another_http_attempt(self):
        from definalyzer.market_data import _fetch_json_with_backoff
        event=threading.Event()
        error=HTTPError('https://example.test',429,'limited',{},None)
        with patch('definalyzer.market_data.urlopen',side_effect=error) as request:
            with self.assertRaises(OperationCancelled),cancellation_scope(event):
                _fetch_json_with_backoff('https://example.test',sleep=lambda seconds:event.set())
            self.assertEqual(request.call_count,1)

    def test_cancel_endpoint_requires_token_and_stops_work(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=WorkspaceManager(Path(directory)/'output');manager.initialize()
            server=create_dashboard_server(manager,port=0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def execute(*args,**kwargs):
                while True:
                    kwargs['progress']('Working')
                    time.sleep(.01)
            try:
                with patch('definalyzer.dashboard._execute_job',side_effect=execute):
                    job=server.jobs.submit(action='provider-test',project=None,payload={})
                    url=f'http://127.0.0.1:{server.server_port}/api/jobs/{job["job_id"]}/cancel'
                    with self.assertRaises(HTTPError) as error:
                        urlopen(Request(url,data=b'{}',headers={'Content-Type':'application/json'}))
                    self.assertEqual(error.exception.code,403);error.exception.close()
                    with urlopen(Request(url,data=b'{}',headers={'Content-Type':'application/json','X-DEFINALYZER-Token':server.token})) as response:
                        self.assertEqual(response.status,202)
                    for _ in range(100):
                        if server.jobs.get(job['job_id'])['status']=='cancelled':break
                        time.sleep(.01)
                    self.assertEqual(server.jobs.get(job['job_id'])['status'],'cancelled')
            finally:
                server.jobs.close();server.shutdown();server.server_close();thread.join(timeout=2)
