"""Exercise the exact audio operations Ming needs, without loading model weights."""
import tempfile
import unittest
from pathlib import Path
import torch
import torchaudio
from torchaudio.compliance.kaldi import fbank


class AudioRuntimeTests(unittest.TestCase):
    def test_reference_audio_and_speaker_features(self):
        path = Path(__file__).parent / "upstream/data/voice_presets/voice_audio/lingguang.wav"
        waveform, rate = torchaudio.load(path, backend="soundfile")
        mono = waveform.mean(0, keepdim=True)
        speech = torchaudio.transforms.Resample(rate, 16000)(mono)
        features = fbank(speech, num_mel_bins=80, dither=0, sample_frequency=16000)
        self.assertGreater(features.shape[0], 100)
        self.assertEqual(features.shape[1], 80)
        self.assertTrue(torch.isfinite(features).all())
        self.assertGreater(speech.square().mean().item(), 1e-6)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audio.wav"
            torchaudio.save(str(output), speech, 16000, backend="soundfile")
            restored, restored_rate = torchaudio.load(output, backend="soundfile")
            self.assertEqual(restored_rate, 16000)
            self.assertEqual(restored.shape, speech.shape)
            self.assertLess((restored - speech).abs().max().item(), 1e-3)


if __name__ == "__main__":
    unittest.main()
