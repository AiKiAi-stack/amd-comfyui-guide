import unittest
import json
import struct
from platform_catalog import ROOT, MODELS
from build_platform_report import TRIAL_NOTES
from build_platform_report import platform_panel, display_status

class ReportPresentationTests(unittest.TestCase):
    def record(self, key, images=None, verdict='失败', execution='error'):
        return {'id':key,'case_id':key,'title':'同一个功能','verdict':verdict,
                'execution':execution,'review':'原评价保留','images':images or [],
                'platform':'Linux','model_id':'qwen-base','feature_id':'color'}
    def test_trials_read_oldest_first_and_are_hidden_until_requested(self):
        first=self.record('first')
        last=self.record('last',['output.png'],'达到目标','success')
        content=platform_panel('Linux',[first,last],{})
        self.assertIn('class="test-history"',content)
        self.assertLess(content.index('id="first"'),content.index('id="last"'))
        self.assertIn('为什么再测',content)
        self.assertIn('本次改动',content)
    def test_every_linux_attempt_has_a_reason_and_matching_source(self):
        catalog=json.loads((ROOT/'workflows/catalog.json').read_text())
        for record in catalog['records']:
            if record['platform']!='Linux':continue
            note=TRIAL_NOTES[record['id']]
            self.assertEqual(note['source_sha256'],record['source_sha256'])
            for field in ('label','purpose','change','result'):
                self.assertTrue(note[field],(record['id'],field))

    def test_scope_contains_only_the_seven_tested_series(self):
        catalog=json.loads((ROOT/'workflows/catalog.json').read_text())
        self.assertEqual(set(MODELS), {'qwen-base','qwen-turbo','kroma','moss','flux2','zimage-gguf','zimage-aio'})
        self.assertEqual(len(catalog['records']),162)
        self.assertEqual(len({(r['model_id'],r['feature_id']) for r in catalog['records']}),40)
        self.assertTrue(all(r['model_id'] in MODELS for r in catalog['records']))
        self.assertEqual(sum(r['platform']=='Windows' for r in catalog['records']),95)

    def test_images_reserve_their_actual_non_square_dimensions(self):
        catalog=json.loads((ROOT/'workflows/catalog.json').read_text())
        record=next(r for r in catalog['records'] if r['case_id']=='flux2-teapot-structure-linux-repair' and r['platform']=='Linux')
        with (ROOT/record['images'][0]).open('rb') as stream:header=stream.read(24)
        width,height=struct.unpack('>II',header[16:24])
        self.assertNotEqual(width,height)
        content=platform_panel('Linux',[record],{})
        self.assertIn(f'width="{width}" height="{height}"',content)

    def test_status_terms_are_small_and_consistent(self):
        for source,expected in [('达到本例目标','通过'),('执行通过 · 提示细节部分达到','部分达到'),('未达到水彩风格目标','未达到'),('中止 · 无输出','未出图'),('未验证','未测试')]:
            record=self.record('fixture',[] if expected in ('未出图','未测试') else ['x.png'],source,'未执行' if expected=='未测试' else 'success')
            self.assertEqual(display_status(record)[0],expected)

if __name__=='__main__':unittest.main()
