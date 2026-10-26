"""Load only the stock checkpoint components needed by an isolated phase."""


def _load(ckpt_name, *, model, clip, vae):
    import comfy.sd
    import folder_paths
    return comfy.sd.load_checkpoint_guess_config(
        folder_paths.get_full_path_or_raise('checkpoints', ckpt_name),
        output_model=model, output_clip=clip, output_vae=vae,
        output_clipvision=False, embedding_directory=folder_paths.get_folder_paths('embeddings'))


class LoadCheckpointClipOnly:
    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        return {'required': {'ckpt_name': (folder_paths.get_filename_list('checkpoints'),)}}

    RETURN_TYPES = ('CLIP',)
    FUNCTION = 'load'
    CATEGORY = 'repair/experimental'

    def load(self, ckpt_name):
        _, clip, _, _ = _load(ckpt_name, model=False, clip=True, vae=False)
        return (clip,)


class LoadCheckpointModelVaeOnly:
    INPUT_TYPES = LoadCheckpointClipOnly.INPUT_TYPES
    RETURN_TYPES = ('MODEL', 'VAE')
    FUNCTION = 'load'
    CATEGORY = 'repair/experimental'

    def load(self, ckpt_name):
        model, _, vae, _ = _load(ckpt_name, model=True, clip=False, vae=True)
        return model, vae


NODE_CLASS_MAPPINGS = {cls.__name__: cls for cls in (LoadCheckpointClipOnly, LoadCheckpointModelVaeOnly)}
