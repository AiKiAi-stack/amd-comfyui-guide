"""Audit real generated outputs and their phase/source bindings, not semantic quality."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image, ImageStat

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from platform_catalog import is_generated_image, sha
HERE=Path(__file__).resolve().parent
findings=[]
for case in json.loads((HERE/'plan.json').read_text()):
    folder=HERE/'cases'/case['case_id'];path=folder/'execution.json'
    if not path.exists():continue
    result=json.loads(path.read_text());graph=json.loads((ROOT/case['workflow']).read_text())
    assert result['workflow_sha256']==sha(ROOT/case['workflow']),case['case_id']
    images=[]
    for image in result['images']:
        if not is_generated_image(image['file'],graph):continue
        output=folder/image['file'];assert sha(output)==image['sha256'],str(output)
        with Image.open(output) as picture:
            rgb=picture.convert('RGB');assert list(rgb.size)==image['size']
            assert hashlib.sha256(rgb.tobytes()).hexdigest()==image['rgb_sha256']
            stats=ImageStat.Stat(rgb)
            assert max(stats.stddev)>2,'Nearly uniform output: '+str(output)
            images.append({'file':output.resolve().relative_to(ROOT).as_posix(),'size':list(rgb.size),'sha256':sha(output),'channel_stddev':stats.stddev})
    if result['status']=='success' and images:
        if result.get('staged'):
            assert result['encoding_pid']!=result['sampling_pid']
            assert result['encoding_exited_before_sampling'] is True
            for phase in result.get('phase_names', ['encode','sample']):
                phasefolder=folder.parent/(case['case_id']+'--'+phase)
                phase_result=json.loads((phasefolder/'execution.json').read_text())
                assert phase_result['status']=='success'
                assert phase_result['workflow_sha256']==sha(phasefolder/'workflow.api.json')
            archive=ROOT/'runtime/ubuntu/ComfyUI/input'/result['conditioning_archive']
            assert sha(archive)==result['conditioning_sha256']
            if result.get('caption_archive'):
                assert result['caption_exited_before_encoding'] is True
                assert len({result['caption_pid'],result['encoding_pid'],result['sampling_pid']})==3
                assert sha(ROOT/'runtime/ubuntu/ComfyUI/input'/result['caption_archive'])==result['caption_archive_sha256']
                assert sha(ROOT/result['caption_text_file'])==result['caption_text_sha256']
                first=json.loads((folder.parent/(case['case_id']+'--caption')/'execution.json').read_text())
                assert first['outputs']['repair_save_caption']['caption'][0]==result['caption_text']
                second=json.loads((folder.parent/(case['case_id']+'--encode')/'workflow.api.json').read_text())
                assert any(n['class_type']=='LoadRepairText' and n['inputs']['expected_sha256']==result['caption_archive_sha256'] for n in second.values())
        review=json.loads((folder/'review.json').read_text())
        assert review.get('visual_inspected') is True,'Missing visual review '+case['case_id']
        findings.append({'case':case['case_id'],'model':case['model_id'],'feature':case['feature_id'],'verdict':review['verdict'],'staged':bool(result.get('staged')),'images':images})
result={'scope':'PNG integrity, nonuniform pixels, exact RGB binding, source/phase/archive SHA256 and human review present; not independent semantic or identity acceptance.',
        'successful_case_count':len(findings),'generated_images':sum(len(row['images']) for row in findings),'cases':findings}
(HERE/'generated-images.audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))
