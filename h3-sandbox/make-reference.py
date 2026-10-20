from pathlib import Path
from PIL import Image, ImageDraw

out = Path(__file__).resolve().parent.parent / "trials" / "2026-10-19-h3" / "input" / "cyan-robot-reference.png"
out.parent.mkdir(parents=True, exist_ok=True)
im = Image.new("RGB", (320, 320), "#f4e9d8")
d = ImageDraw.Draw(im)
d.rounded_rectangle((88, 58, 232, 204), radius=26, fill="#17b6c5", outline="#0a5161", width=5)
d.rectangle((106, 77, 214, 145), fill="#f8f1e6", outline="#0a5161", width=4)
d.rectangle((126, 100, 143, 116), fill="#171f2b")
d.rectangle((177, 100, 194, 116), fill="#171f2b")
d.arc((140, 114, 180, 137), 0, 180, fill="#171f2b", width=3)
d.polygon([(101, 177), (213, 177), (234, 191), (201, 206), (120, 202), (85, 191)], fill="#d63992")
d.rounded_rectangle((111, 206, 210, 284), radius=16, fill="#17b6c5", outline="#0a5161", width=5)
d.line((87, 223, 54, 185), fill="#0a5161", width=16)
d.ellipse((43, 170, 64, 191), fill="#17b6c5", outline="#0a5161", width=4)
d.line((234, 222, 274, 250), fill="#0a5161", width=16)
d.ellipse((266, 244, 288, 265), fill="#17b6c5", outline="#0a5161", width=4)
im.save(out)
print(out)
