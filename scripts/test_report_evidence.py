import unittest
from report_evidence import native_seconds, comparison
from build_platform_report import record_html

class ReportEvidenceTests(unittest.TestCase):
    def test_history_duration_excludes_wait_before_execution(self):
        self.assertEqual(native_seconds({'p': {'status': {'messages': [
            ['execution_start', {'timestamp': 1000}], ['execution_success', {'timestamp': 3500}]]}}}), 2.5)
    def test_same_files_do_not_establish_a_controlled_benchmark(self):
        item = {'recipe_conditions': {'diffusion_files': ['same.gguf'], 'encoder_files': ['a'], 'input_sha256_ordered': []}}
        other = {'recipe_conditions': {**item['recipe_conditions'], 'encoder_files': ['b']}}
        result = comparison(item, other)
        self.assertFalse(result['controlled'])
        self.assertIn('文本/视觉编码器', result['differences'])
    def test_record_shows_scope_and_does_not_call_phase_gpu_time(self):
        record = {'id':'test', 'case_id':'test', 'title':'test', 'verdict':'通过',
            'execution':'success', 'review':'ok', 'images':[], 'elapsed_seconds':12,
            'timing': {'scope':'含编码与解码', 'reported_seconds':12, 'phases':[]}}
        rendered = record_html(record, None)
        self.assertIn('计时范围', rendered)
        self.assertIn('含编码与解码', rendered)
        self.assertIn('GPU纯采样时间未单独记录', rendered)

if __name__ == '__main__': unittest.main()
