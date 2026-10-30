"""Inspect verified weight headers without importing torch or creating tensors."""
import json
import math
import struct
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
records=[]
for item in json.loads((HERE/'download-manifest.json').read_text(encoding='utf-8')):
    path=Path(item['target'])
    receipt=json.loads((HERE/(path.name+'.verified.json')).read_text(encoding='utf-8'))
    assert path.stat().st_size==item['bytes'] and receipt['verified_sha256']==item['sha256']
    record={'file':str(path),'bytes':path.stat().st_size,'verified_sha256':receipt['verified_sha256']}
    with path.open('rb') as source:
        if path.suffix=='.gguf':
            magic,version,tensors,metadata=struct.unpack('<4sIQQ', source.read(24))
            assert magic==b'GGUF'
            record.update(format='GGUF',version=version,tensor_count=tensors,metadata_count=metadata)
        else:
            length=struct.unpack('<Q',source.read(8))[0]
            assert 0<length<64*1024*1024
            header=json.loads(source.read(length))
            tensors={k:v for k,v in header.items() if k!='__metadata__'}
            for tensor in tensors.values():
                start,end=tensor['data_offsets']
                assert 0<=start<=end<=path.stat().st_size-8-length
            record.update(format='safetensors',tensor_count=len(tensors),
                          dtype_counts=dict(Counter(t['dtype'] for t in tensors.values())),
                          tensor_elements=sum(math.prod(t['shape']) for t in tensors.values()),
                          prefixes=dict(Counter('.'.join(k.split('.')[:2]) for k in tensors)),
                          metadata=header.get('__metadata__',{}))
    records.append(record)
(HERE/'weight-header-audit.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k not in ('prefixes','metadata')} for r in records],indent=2))
