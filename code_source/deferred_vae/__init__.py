"""Opt-in scheduling dependency for VAE loading after a latent is ready."""


class LoadVaeAfterSampling:
    @classmethod
    def INPUT_TYPES(cls):
        from nodes import VAELoader
        return {'required': {**VAELoader.INPUT_TYPES()['required'], 'after_sampling': ('LATENT',)}}

    RETURN_TYPES = ('VAE',)
    FUNCTION = 'load'
    CATEGORY = 'repair/experimental'

    def load(self, vae_name, after_sampling):
        from nodes import VAELoader
        return VAELoader().load_vae(vae_name)


NODE_CLASS_MAPPINGS = {'LoadVaeAfterSampling': LoadVaeAfterSampling}
NODE_DISPLAY_NAME_MAPPINGS = {'LoadVaeAfterSampling': 'Load VAE after sampling'}
