import importlib
import importlib.util
import unittest
import sqlite3

class StubRuntime:
    def read_case(self,unit_id,layer='hit'):
        if isinstance(unit_id,list):raise sqlite3.ProgrammingError('unsupported SQLite parameter')
        return dict(unit_id=unit_id,layer=layer)
    def close(self):raise AssertionError('private method was called')

class RuntimeCliTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('runtime_cli'),'CLI not implemented')
        return importlib.import_module('runtime_cli')
    def test_registered_tool_dispatches_named_parameters(self):
        got=self.module().dispatch(StubRuntime(),dict(operation='read_case',arguments=dict(unit_id='U',layer='extended')))
        self.assertEqual(got,dict(unit_id='U',layer='extended'))
    def test_private_methods_and_malformed_requests_refused(self):
        for request in [None,dict(operation='close',arguments={}),dict(operation='read_case',arguments=[]),dict(operation='read_case',arguments={},extra='ignored?')]:
            with self.subTest(request=request),self.assertRaises(ValueError):self.module().dispatch(StubRuntime(),request)
    def test_bad_database_parameter_does_not_kill_persistent_worker(self):
        m=self.module();runtime=StubRuntime()
        bad=m.handle_line(runtime,'{"operation":"read_case","arguments":{"unit_id":[]}}')
        good=m.handle_line(runtime,'{"operation":"read_case","arguments":{"unit_id":"U"}}')
        self.assertFalse(bad['ok']);self.assertTrue(good['ok']);self.assertEqual(good['result']['unit_id'],'U')

if __name__=='__main__':unittest.main()
