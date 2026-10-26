# Load VAE after sampling

This opt-in node delegates unchanged to the installed core `VAELoader`, after
its required `LATENT` input is ready. It changes dependency order, without
changing the VAE file, precision, decoder or latent.

For the recorded pure text Qwen graph, remove the encoder's unused optional VAE
input and connect sampler output to `after_sampling`. The decoder still uses
the same VAE. Do not create this dependency when the encoder needs a VAE for
reference images: that would introduce a graph cycle. The trial runner refuses
known reference/unknown input forms before inserting this node.

See `trials/2026-10-24-ubuntu-followup/` for whole-graph controls and bounded
memory measurements. Loading order alone did not fix the recorded partial CPU
offload stall; it is tested alongside the explicit CLIP CPU backing policy.
