"""Measure outside-mask preservation from a replay's saved input/mask/output PNGs."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def mask_support(graph, key):
    node = graph[key]
    inputs = node["inputs"]
    if node["class_type"] == "SolidMask":
        return np.full((inputs["height"], inputs["width"]), inputs["value"] > 0, dtype=bool)
    if node["class_type"] == "FeatherMask":
        # Core FeatherMask uses (index+1)/width: every feather factor is
        # positive. Its four tiny corner values can quantize to zero in PNG.
        return mask_support(graph, inputs["mask"][0])
    if node["class_type"] == "MaskComposite" and inputs["operation"] == "add":
        destination = mask_support(graph, inputs["destination"][0]).copy()
        source = mask_support(graph, inputs["source"][0])
        x, y = inputs["x"], inputs["y"]
        left, top = max(x, 0), max(y, 0)
        right, bottom = min(x + source.shape[1], destination.shape[1]), min(y + source.shape[0], destination.shape[0])
        if right > left and bottom > top:
            destination[top:bottom, left:right] |= source[top-y:bottom-y, left-x:right-x]
        return destination
    raise ValueError("Exact mask support unavailable for " + node["class_type"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    result = json.loads((args.case / "result.json").read_text(encoding="utf-8"))
    graph = json.loads((args.case / "api.json").read_text(encoding="utf-8"))
    images = [args.case / image["file"] for image in result["images"]]
    main_key = next(key for key, node in graph.items() if node["class_type"] == "SaveImage" and
                    graph[node["inputs"]["images"][0]]["class_type"] == "ImageCompositeMasked")
    composite = graph[graph[main_key]["inputs"]["images"][0]]
    mask_key = next(key for key, node in graph.items() if node["class_type"] == "SaveImage" and
                    graph[node["inputs"]["images"][0]]["class_type"] == "MaskToImage")
    input_key = next(key for key, node in graph.items() if node["class_type"] == "SaveImage" and
                     node["inputs"]["images"] == composite["inputs"]["destination"])

    def saved_image(node_key):
        matches = [path for path in images if path.name.startswith(node_key + "-")]
        if len(matches) != 1:
            raise ValueError("Expected one image for each input/mask/output node")
        return matches[0]

    mask, source, main = map(saved_image, (mask_key, input_key, main_key))
    original = np.asarray(Image.open(source).convert("RGB"), dtype=np.int16)
    output = np.asarray(Image.open(main).convert("RGB"), dtype=np.int16)
    mask_values = np.asarray(Image.open(mask).convert("L"))
    if output.shape != original.shape or output.shape[:2] != mask_values.shape:
        raise ValueError("Input, mask and output dimensions differ")
    difference = np.abs(output - original)
    outside = mask_values == 0
    measurement = {"outside_pixels": int(outside.sum()),
        "outside_changed_pixels": int((difference[outside].max(axis=1) > 0).sum()),
        "outside_max_channel_difference": int(difference[outside].max()),
        "inside_pixels": int((~outside).sum()),
        "basis": "8-bit saved mask PNG; tiny positive feather corners may quantize to zero",
        "meaning": "Outside preservation is provided by final compositing, not attributed solely to the model."}
    mask_save = graph[mask_key]
    if mask_save:
        try:
            converter = graph[mask_save["inputs"]["images"][0]]
            support = mask_support(graph, converter["inputs"]["mask"][0])
            exact_outside = ~support
            measurement["float_mask_support"] = {"outside_pixels": int(exact_outside.sum()),
                "outside_changed_pixels": int((difference[exact_outside].max(axis=1) > 0).sum()),
                "outside_max_channel_difference": int(difference[exact_outside].max()),
                "basis": "Boolean support reconstructed from actual SolidMask/FeatherMask/add graph"}
        except ValueError as error:
            measurement["float_mask_support_unavailable"] = str(error)
    (args.case / "mask-measurement.json").write_text(json.dumps(measurement, indent=2), encoding="utf-8")
    print(json.dumps(measurement))


if __name__ == "__main__":
    main()
