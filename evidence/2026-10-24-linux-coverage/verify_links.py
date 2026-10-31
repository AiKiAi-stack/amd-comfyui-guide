"""Check local report links and anchors against files that actually exist."""
from html.parser import HTMLParser
from pathlib import Path
import json
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'report/index.html'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.links=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if values.get('id'):self.ids.add(values['id'])
        for field in ['href','src']:
            if values.get(field):self.links.append(values[field])
parser=Links();parser.feed(REPORT.read_text());missing=[];local=0;anchors=0
for value in parser.links:
    parsed=urlsplit(value)
    if parsed.scheme or parsed.netloc:continue
    if not parsed.path:
        if parsed.fragment:
            anchors+=1
            if unquote(parsed.fragment) not in parser.ids:missing.append(value)
        continue
    target=(REPORT.parent/unquote(parsed.path)).resolve();local+=1
    if not target.exists():missing.append(value)
result={'local_file_references':local,'anchors':anchors,'missing':missing}
(Path(__file__).resolve().parent/'report-links.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False));assert not missing
