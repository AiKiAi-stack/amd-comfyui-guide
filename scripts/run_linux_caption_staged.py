"""Preserve exact generated text, conditioning and samples across three processes."""
import copy
import json
import time
from pathlib import Path

from platform_catalog import ROOT, sha
from run_conditioned_repair import prune, conditioning_node

TRIAL=ROOT/'evidence/2026-10-24-linux-coverage'


def execute_caption_staged(case, timeout, execute, write_result):
    folder=TRIAL/'cases'/case['case_id'];destination=folder/'execution.json'
    if destination.exists():
        old=json.loads(destination.read_text())
        if old['status']=='success' and old['images']:return old
        destination.rename(folder/('execution.previous-'+str(time.time_ns())+'.json'))
    source=ROOT/case['workflow'];graph=json.loads(source.read_text());digest=sha(source)
    sampler=next(k for k,n in graph.items() if n['class_type'] in ('KSampler','SamplerCustomAdvanced'))
    conditioner=conditioning_node(graph,sampler);outputs=[k for k,n in graph.items() if n['class_type']=='SaveImage']
    phases=[]

    def phase(role, workflow):
        item=copy.deepcopy(case);item['case_id']+='--'+role
        item['profile_args']=case['phase_profile_args'].get(role,case['profile_args'])
        directory=TRIAL/'cases'/item['case_id'];directory.mkdir(exist_ok=True)
        path=directory/'workflow.api.json';content=json.dumps(workflow,ensure_ascii=False,indent=2)+'\n'
        if path.exists() and path.read_text()!=content:raise ValueError('Phase graph changed; use a new case ID')
        if not path.exists():path.write_text(content)
        item['workflow']=path.relative_to(ROOT).as_posix();result=execute(item,timeout);phases.append(role)
        return result

    def failed(result, role):
        value=copy.deepcopy(result);value.update(case_id=case['case_id'],staged=True,failed_phase=role,
            phase_names=phases,workflow_sha256=digest,phase_workflow_sha256=result['workflow_sha256'])
        write_result(destination,value);return value

    def archive(result, node):
        ui=result['outputs'][node];relative,digest=ui['text'][0],ui['archive_sha256'][0]
        root=(ROOT/'runtime/ubuntu/ComfyUI/input/repair_conditioning').resolve()
        path=(ROOT/'runtime/ubuntu/ComfyUI/input'/relative).resolve()
        if not path.is_relative_to(root) or sha(path)!=digest:raise ValueError('Archive path/hash changed')
        return relative,digest

    caption=copy.deepcopy(graph)
    caption['repair_save_caption']={'class_type':'SaveRepairText','inputs':{
        'text':graph['4']['inputs']['prompt'],'prefix':case['case_id']+'-caption','workflow_sha256':digest}}
    first=phase('caption',prune(caption,['repair_save_caption']))
    if first['status']!='success':return failed(first,'caption')
    text_file,text_sha=archive(first,'repair_save_caption')
    text=first['outputs']['repair_save_caption']['caption'][0]
    (folder/'caption.txt').write_text(text+'\n')
    encoded=copy.deepcopy(graph)
    prompt_node=graph['4']['inputs']['prompt'][0]
    encoded[prompt_node]={'class_type':'LoadRepairText','inputs':{'file':text_file,'expected_sha256':text_sha}}
    encoded['repair_save_conditions']={'class_type':'SaveRepairConditioning','inputs':{
        'positive':graph[conditioner]['inputs']['positive'],'negative':graph[conditioner]['inputs']['negative'],
        'latent':graph[sampler]['inputs']['latent_image'],'prefix':case['case_id']+'-conditions','workflow_sha256':digest}}
    second=phase('encode',prune(encoded,['repair_save_conditions']))
    if second['status']!='success':return failed(second,'encoding')
    condition_file,condition_sha=archive(second,'repair_save_conditions')
    sampled=copy.deepcopy(graph)
    sampled['repair_load_conditions']={'class_type':'LoadRepairConditioning','inputs':{'file':condition_file,'expected_sha256':condition_sha}}
    for name,slot in [('positive',0),('negative',1)]:sampled[conditioner]['inputs'][name]=['repair_load_conditions',slot]
    sampled[sampler]['inputs']['latent_image']=['repair_load_conditions',2]
    third=phase('sample',prune(sampled,outputs));value=copy.deepcopy(third)
    value.update(case_id=case['case_id'],staged=True,phase_names=phases,workflow_sha256=digest,
        caption_text=text,caption_text_file=(folder/'caption.txt').relative_to(ROOT).as_posix(),caption_text_sha256=sha(folder/'caption.txt'),
        caption_archive=text_file,caption_archive_sha256=text_sha,conditioning_archive=condition_file,conditioning_sha256=condition_sha,
        caption_pid=first['pid'],encoding_pid=second['pid'],sampling_pid=third['pid'],
        caption_exited_before_encoding=True,encoding_exited_before_sampling=True,
        caption_command=first['command'],encoding_command=second['command'],encoding_environment=second['environment'],
        caption_seconds=first['elapsed_seconds'],encoding_seconds=second['elapsed_seconds'],sampling_seconds=third['elapsed_seconds'],
        elapsed_seconds=sum(x['elapsed_seconds'] for x in [first,second,third]),total_seconds=sum(x['total_seconds'] for x in [first,second,third]),
        minimum_available_ram_mib=min(x['minimum_available_ram_mib'] for x in [first,second,third]))
    for image in value['images']:image['file']='../'+case['case_id']+'--sample/'+image['file']
    write_result(destination,value);print('CAPTION_STAGED_DONE',case['case_id'],value['status'],flush=True)
    return value
