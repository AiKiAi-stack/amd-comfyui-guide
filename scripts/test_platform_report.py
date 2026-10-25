"""Regression checks for evidence boundaries and portable workflow semantics."""
import json
import hashlib
import re
from pathlib import Path
import unittest

from platform_catalog import ROOT, HERE, catalog_records, feature_id, is_generated_image, model_id, sha, standalone_graph
from build_platform_report import escape, platform_panel, verdict_class


class PlatformReportTests(unittest.TestCase):
    def test_negative_pass_word_is_not_a_success_badge(self):
        for verdict in ['未通过', '不通过', '未达标']:
            self.assertEqual(verdict_class(verdict), 'bad')

    def test_auxiliary_caption_keeps_three_verified_phase_boundaries(self):
        records = [r for r in self.catalog['records'] if r.get('three_phase_caption') and r['images']]
        self.assertEqual(len(records), 1)
        record = records[0]
        result = json.loads((ROOT / record['source_case_file']).read_text())
        self.assertEqual(result['phase_names'], ['caption', 'encode', 'sample'])
        self.assertEqual(len({result['caption_pid'], result['encoding_pid'], result['sampling_pid']}), 3)
        jobs = {j['phase']: j for j in self.catalog['workflows'] if j['id'] in record['phase_workflow_ids']}
        self.assertEqual({j['phase_order'] for j in jobs.values()}, {1, 2, 3})
        self.assertIn('--cpu', jobs['encode']['launch_args'])
        self.assertNotIn('--cpu', jobs['caption']['launch_args'])
        self.assertNotIn('--cpu', jobs['sample']['launch_args'])
        caption = json.loads((ROOT / jobs['caption']['api']).read_text())
        encoded = json.loads((ROOT / jobs['encode']['api']).read_text())
        sampled = json.loads((ROOT / jobs['sample']['api']).read_text())
        self.assertTrue(any(n['class_type'] == 'TextGenerate' for n in caption.values()))
        self.assertTrue(any(n['class_type'] == 'LoadRepairText' and n['inputs']['expected_sha256'] == result['caption_archive_sha256'] for n in encoded.values()))
        self.assertFalse(any(n['class_type'] == 'TextGenerate' for n in encoded.values()))
        self.assertFalse(any('CLIPLoader' in n['class_type'] for n in sampled.values()))
        first = json.loads((ROOT / jobs['caption']['source']).with_name('execution.json').read_text())
        self.assertEqual(first['outputs']['repair_save_caption']['caption'][0], record['caption_text'])
        self.assertFalse(next(j for j in self.catalog['workflows'] if j['id'] == record['id'])['execution_verified_linux'])

    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'workflows/catalog.json').read_text())

    def test_windows_sources_and_complete_archive_are_preserved(self):
        before = json.loads((ROOT / 'trials/2026-10-25-report-audit/scope-preservation.json').read_text())
        articles = {m[1].decode(): hashlib.sha256(m[0]).hexdigest() for m in re.finditer(
            rb'<article\b[^>]*\bid="([^"]+)"[^>]*>.*?</article>',
            (HERE / 'feature-report.windows-20261024.html').read_bytes(), re.S)}
        self.assertEqual(articles, before['archived_articles_sha256'])

    def test_every_original_windows_case_and_review_remains(self):
        expected = {r['id']: r for r in json.loads((ROOT / 'trials/2026-10-25-report-audit/preserved-windows.json').read_text())}
        actual = {r['id']: r for r in self.catalog['records'] if r['id'] in expected}
        self.assertEqual(len(actual), 95)
        for key, record in expected.items():
            for field in ('verdict', 'review', 'original_case', 'source_sha256'):
                self.assertEqual(actual[key][field], record[field], (key, field))

    def test_linux_execution_is_never_inherited_from_windows(self):
        verified = [j for j in self.catalog['workflows'] if j['execution_verified_linux']]
        baseline = {'linux-qwen-blue', 'linux-qwen-green', 'linux-zimage-1', 'linux-zimage-2'}
        self.assertTrue(baseline <= {j['id'] for j in verified})
        self.assertTrue(all(j['platform'] == 'Linux' for j in verified))
        records = {r['id']: r for r in self.catalog['records']}
        for job in verified:
            self.assertEqual(records[job['id']]['execution'], 'success')
            self.assertTrue(records[job['id']]['images'])
            self.assertFalse(records[job['id']]['blocked'])

    def test_model_family_uses_diffusion_weight_not_un_encoder(self):
        encoder = {'2': {'class_type': 'CLIPLoaderGGUF', 'inputs': {'clip_name': 'qwen-un.gguf'}}}
        for weight, family in [('qwen-image-2.1-Q4_K_M.gguf', 'qwen-base'), ('qwen-image-2.1-turbo-Q4_K_M.gguf', 'qwen-turbo')]:
            graph = dict(encoder, **{'1': {'class_type': 'UnetLoaderGGUF', 'inputs': {'unet_name': weight}}})
            self.assertEqual(model_id({'id': 'example', 'model': 'Qwen'}, graph), family)

    def test_batch_wait_barrier_is_bypassed_without_other_case(self):
        graph = {'c': {'class_type': 'Text', 'inputs': {'text': 'ours'}},
                 'other': {'class_type': 'Text', 'inputs': {'text': 'not ours'}},
                 'barrier': {'class_type': 'BenchmarkConditioningBarrier', 'inputs': {'conditioning': ['c', 0], 'ready_1': ['other', 0]}},
                 'out': {'class_type': 'SaveImage', 'inputs': {'images': ['barrier', 0], 'filename_prefix': 'unique-case'}},
                 'other-out': {'class_type': 'SaveImage', 'inputs': {'images': ['other', 0], 'filename_prefix': 'unrelated'}}}
        extracted, _ = standalone_graph(graph, 'unique-case')
        self.assertEqual(set(extracted), {'c', 'out'})
        self.assertEqual(extracted['out']['inputs']['images'], ['c', 0])
        self.assertEqual(graph['out']['inputs']['images'], ['barrier', 0])

    def test_generated_reference_material_is_not_an_edit_result(self):
        self.assertEqual(feature_id({'id': 'kroma-opd-q2-t2i-fox-512', 'recipe': 't2i', 'feature': '文生图：狐狸'}, 'kroma'), 't2i')
        self.assertEqual(feature_id({'id': 'kroma-style-source', 'recipe': 't2i', 'feature': '文生图素材：风格参考'}, 'kroma'), 't2i')
        self.assertEqual(feature_id({'id': 'qwen-base-edit-orange-to-white-cat-512', 'recipe': 'edit'}, 'qwen-base'), 'color')

    def test_portable_graph_preserves_every_non_image_input(self):
        for job in self.catalog['workflows']:
            source = ROOT / job['source']
            self.assertEqual(sha(source), job['source_sha256'])
            expected, _ = standalone_graph(json.loads(source.read_text(encoding='utf-8-sig')), job['case_id'])
            actual = json.loads((ROOT / job['api']).read_text())
            self.assertEqual(set(expected), set(actual))
            for key, node in expected.items():
                for field, value in node['inputs'].items():
                    if node['class_type'] == 'LoadImage' and field == 'image':
                        continue
                    self.assertEqual(actual[key]['inputs'][field], value, (job['id'], key, field))
            for asset in job['inputs']:
                if not asset['available']: continue
                packaged = ROOT / 'workflows/input' / asset['file']
                self.assertEqual(sha(packaged), self.catalog['input_assets'][asset['file']]['sha256'])
                self.assertEqual(sha(packaged), sha(ROOT / 'runtime/ubuntu/ComfyUI/input' / asset['file']))

    def test_only_checked_graphs_are_installed(self):
        receipt = json.loads((ROOT / 'trials/2026-10-24-platform-report/installation.json').read_text())
        approved = {j['id'] for j in self.catalog['workflows'] if j.get('frontend_import', {}).get('pass') and j.get('install_recommended', True)}
        self.assertEqual({r['id'] for r in receipt['installed']}, approved)
        self.assertGreaterEqual(len(approved), 99)
        for row in receipt['installed']:
            self.assertEqual(sha(Path(row['installed'])), row['sha256'])

    def test_report_escapes_prompt_markup(self):
        self.assertEqual(escape('<script>"&'), '&lt;script&gt;&quot;&amp;')

    def test_staged_outputs_never_claim_whole_graph_execution(self):
        for job in self.catalog['workflows']:
            if job.get('staged_result'):
                self.assertFalse(job['execution_verified_linux'], job['id'])
            for dependency in job.get('cache_dependencies', []):
                if dependency['available']:
                    self.assertEqual(sha(ROOT / 'workflows/input' / dependency['file']), dependency['sha256'])

    def test_later_failed_attempts_do_not_hide_existing_linux_output(self):
        record = {'id': 'success', 'case_id': 'success', 'title': 'Example', 'verdict': '通过',
                  'review': 'Original actual output', 'execution': 'success', 'images': ['existing.png']}
        failed = {**record, 'id': 'failed', 'case_id': 'failed', 'verdict': '失败', 'execution': 'error', 'images': []}
        content = platform_panel('Linux', [record, failed, {**failed, 'id': 'failed-2'}], {})
        self.assertIn('<img', content)
        self.assertIn('existing.png', content)
        self.assertIn('失败', content)

    def test_input_and_mask_previews_never_count_as_generated_linux_output(self):
        graph = {'source': {'class_type': 'LoadImage', 'inputs': {'image': 'input.png'}},
                 'sample': {'class_type': 'KSampler', 'inputs': {}},
                 'decode': {'class_type': 'VAEDecode', 'inputs': {'samples': ['sample', 0]}},
                 '7': {'class_type': 'SaveImage', 'inputs': {'images': ['decode', 0]}},
                 '59': {'class_type': 'SaveImage', 'inputs': {'images': ['source', 0]}}}
        self.assertTrue(is_generated_image('../case--sample/7-0.png', graph))
        self.assertFalse(is_generated_image('../case--sample/59-0.png', graph))

    def test_variant_extracts_render_when_preview_prefix_uses_source_case_id(self):
        graph = {'input': {'class_type': 'LoadImage', 'inputs': {'image': 'input.png'}},
                 'sample': {'class_type': 'KSampler', 'inputs': {'latent_image': ['input', 0]}},
                 'out': {'class_type': 'SaveImage', 'inputs': {'images': ['sample', 0], 'filename_prefix': 'original-case'}},
                 'preview': {'class_type': 'SaveImage', 'inputs': {'images': ['input', 0], 'filename_prefix': 'original-case'}}}
        result, _ = standalone_graph(graph, 'original-case-cpu-encode--sample')
        self.assertEqual(set(result), {'input', 'sample', 'out'})


if __name__ == '__main__':
    unittest.main()
