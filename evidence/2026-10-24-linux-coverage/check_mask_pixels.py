"""Compare the saved final composite to its saved source outside a zero mask."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('case',type=Path)
parser.add_argument('--prefix',default='case01_')
args=parser.parse_args()
folder=args.case.resolve();sample=folder.parent/(folder.name+'--sample')
paths={kind:sample/(args.prefix+node+'-0.png') for kind,node in [('source','59'),('mask','58'),('output','7')]}
arrays={kind:np.asarray(Image.open(path).convert('RGB')) for kind,path in paths.items()}
assert len({a.shape for a in arrays.values()})==1
zero=np.all(arrays['mask']==0,axis=-1)
difference=np.abs(arrays['output'].astype(np.int16)-arrays['source'].astype(np.int16))
result={'scope':'Saved final ImageCompositeMasked output only; not raw diffusion decode. Mask zero is measured on the saved 8-bit mask preview.',
        'zero_mask_pixels':int(zero.sum()),'changed_zero_mask_pixels':int(np.any(difference[zero]!=0,axis=-1).sum()),
        'maximum_zero_mask_difference':int(difference[zero].max()) if zero.any() else None,
        'files':{kind:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for kind,path in paths.items()}}
(folder/'mask-protection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
