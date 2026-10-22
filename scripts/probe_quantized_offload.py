"""Exercise installed quantized GPU->CPU unpatch paths without loading a full model.

This is a diagnostic, not proof that full-model OOM recovery is repaired.
Run in its own process; an access violation must remain visible in the exit code.
"""
import argparse
import gc
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--kind', choices=['gguf', 'int8'], required=True)
    parser.add_argument('--gguf', type=Path)
    parser.add_argument('--cycles', type=int, default=200)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.cycles < 1 or args.cycles > 2000:
        parser.error('Use 1..2000 bounded cycles')
    if args.kind == 'gguf' and not args.gguf:
        parser.error('--gguf is required for the GGUF probe')
    args.out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.runtime / 'ComfyUI'))
    sys.argv = [sys.argv[0], '--disable-dynamic-vram', '--lowvram']
    import comfy.options
    comfy.options.enable_args_parsing()
    import torch
    import comfy.model_patcher

    torch.manual_seed(6650)
    cpu, gpu = torch.device('cpu'), torch.device('cuda:0')
    if not torch.cuda.is_available():
        raise RuntimeError('This diagnostic requires the actual GPU offload path')
    record = {'kind': args.kind, 'torch_version': torch.__version__,
              'device': torch.cuda.get_device_name(0), 'requested_cycles': args.cycles,
              'completed_cycles': 0, 'status': 'running',
              'scope': 'One bounded weight; ordinary and synthetic-exception unpatch, not real OOM recovery'}

    if args.kind == 'gguf':
        import gguf
        package = types.ModuleType('repair_probe_gguf')
        package.__path__ = [str(args.runtime / 'ComfyUI/custom_nodes/ComfyUI-GGUF')]
        sys.modules[package.__name__] = package
        ops = importlib.import_module(package.__name__ + '.ops')
        gguf_nodes = importlib.import_module(package.__name__ + '.nodes')
        reader = gguf.GGUFReader(str(args.gguf))
        candidates = [t for t in reader.tensors if t.data.nbytes <= 16 * 1024**2
                      and t.tensor_type not in {gguf.GGMLQuantizationType.F16, gguf.GGMLQuantizationType.F32}]
        tensor = max(candidates, key=lambda t: t.data.nbytes)
        raw = torch.from_numpy(tensor.data)
        weight = ops.GGMLTensor(raw, tensor_type=tensor.tensor_type,
                               tensor_shape=torch.Size(reversed(tensor.shape.tolist())))
        patcher_class = gguf_nodes.GGUFModelPatcher
        def storage(parameter):
            return parameter.as_subclass(torch.Tensor)
        record.update(tensor_name=tensor.name, quantization=tensor.tensor_type.name,
                      storage_bytes=tensor.data.nbytes, logical_shape=list(weight.shape),
                      initial_storage='GGUF reader memory-mapped array retained for probe lifetime')
    else:
        from comfy_kitchen.tensor import QuantizedTensor, TensorWiseINT8Layout
        raw = torch.randint(-120, 120, (2048, 4096), dtype=torch.int8)
        params = TensorWiseINT8Layout.Params(scale=torch.full((2048, 1), 0.02),
            orig_dtype=torch.float16, orig_shape=tuple(raw.shape), convrot=True, convrot_groupsize=256)
        weight = QuantizedTensor(raw, 'TensorWiseINT8Layout', params)
        patcher_class = comfy.model_patcher.ModelPatcher
        def storage(parameter):
            return parameter._qdata
        record.update(storage_bytes=raw.numel(), logical_shape=list(raw.shape), quantization='TensorWiseINT8Layout')

    model = torch.nn.Module()
    model.register_parameter('weight', torch.nn.Parameter(weight, requires_grad=False))
    patcher = patcher_class(model, gpu, cpu)
    expected = hashlib.sha256(storage(model.weight).numpy().tobytes()).hexdigest()
    initial_type = type(model.weight)
    started = time.monotonic()
    progress = args.out / 'progress.jsonl'
    try:
        for cycle in range(args.cycles):
            model.to(gpu)
            assert storage(model.weight).device == gpu
            # Alternate normal cleanup with the same cleanup after a controlled
            # Python exception. Do not pretend this recreates a HIP allocation OOM.
            try:
                if cycle % 2:
                    raise RuntimeError('synthetic execution exception before unpatch')
            except RuntimeError as error:
                if str(error) != 'synthetic execution exception before unpatch':
                    raise
            finally:
                patcher.unpatch_model(device_to=cpu, unpatch_weights=True)
            assert storage(model.weight).device == cpu
            assert type(model.weight) is initial_type
            actual = hashlib.sha256(storage(model.weight).numpy().tobytes()).hexdigest()
            assert actual == expected, 'Quantized storage changed during offload/reload'
            if args.kind == 'int8':
                assert model.weight._params.scale.device == cpu
                assert model.weight._params.orig_dtype == torch.float16
            record['completed_cycles'] = cycle + 1
            with progress.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps({'cycle': cycle + 1, 'storage_sha256': actual}) + '\n')
        # Break ModelPatcher's model/current_patcher reference cycle while its
        # imported modules are still alive, rather than at interpreter shutdown.
        patcher.cleanup()
        del patcher, model
        gc.collect()
        record['explicit_cleanup_completed'] = True
        record['status'] = 'pass_bounded_probe_only'
    finally:
        record.update(elapsed_seconds=round(time.monotonic() - started, 3), storage_sha256=expected)
        (args.out / 'result.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
