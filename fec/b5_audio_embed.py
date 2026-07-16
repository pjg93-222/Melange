# -*- coding: utf-8 -*-
"""Pluggable speaker-embedding backends for the audio-identity layer (2026-07-16 design).

Two backends share one contract — ``embed(samples, sr) -> unit-norm numpy vector`` — so every
consumer (enrollment, verification, diarization) is testable without model weights:

* ``spectral-test``: a deterministic, dependency-light spectral-band embedding used ONLY by the
  test suite and the synthetic battery.  It is NOT a speaker model and must never be used on real
  member audio outside tests; ``for_production`` is False.
* ``ecapa``: SpeechBrain ECAPA-TDNN (spkrec-ecapa-voxceleb) loaded from a LOCAL, explicitly named
  model directory.  The loader hard-refuses when the directory is missing or incomplete and never
  touches the network — model acquisition is a separate, user-approved step whose file SHA-256s
  are recorded in the identity prereg before any calibration run.

Verification semantics live in b5_audio_verify2.py; this module only turns audio into vectors.
"""
from __future__ import annotations

import hashlib
import os

import numpy as np


class BackendRefused(RuntimeError):
    """Raised when a backend cannot run under the declared contract (never silently degraded)."""


def cosine(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denominator = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def _unit(vector):
    vector = np.asarray(vector, dtype=np.float64)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


class SpectralTestBackend:
    """Deterministic log-Mel-band energy embedding for synthetic-fixture tests only.

    Same input samples -> byte-identical vector (no RNG, no model state).  Distinct synthetic
    "voices" (different harmonic stacks) land far apart in cosine; two halves of the same
    synthetic voice land close.  That is all the test suite needs.
    """

    name = "spectral-test"
    for_production = False
    dim = 64

    def embed(self, samples, sr):
        samples = np.asarray(samples, dtype=np.float64)
        if samples.ndim != 1:
            samples = samples.reshape(-1)
        if samples.size < int(0.2 * sr):
            raise BackendRefused("spectral-test: segment shorter than 0.2 s")
        window = int(0.025 * sr)
        hop = int(0.010 * sr)
        if window < 8:
            raise BackendRefused("spectral-test: sample rate too low")
        frames = []
        for start in range(0, samples.size - window, hop):
            frame = samples[start:start + window] * np.hanning(window)
            spectrum = np.abs(np.fft.rfft(frame)) ** 2
            frames.append(spectrum)
        power = np.mean(np.asarray(frames), axis=0)
        edges = np.linspace(0, power.size, self.dim + 1).astype(int)
        bands = np.asarray([power[a:b].sum() for a, b in zip(edges[:-1], edges[1:])])
        return _unit(np.log1p(bands))


class EcapaBackend:
    """SpeechBrain ECAPA-TDNN verification embedding from a pinned local model directory."""

    name = "ecapa"
    for_production = True
    REQUIRED_FILES = ("hyperparams.yaml", "embedding_model.ckpt")

    def __init__(self, model_dir):
        if not model_dir:
            raise BackendRefused(
                "ecapa: --model-dir is required; this backend never downloads weights at runtime")
        model_dir = os.path.abspath(model_dir)
        missing = [name for name in self.REQUIRED_FILES
                   if not os.path.isfile(os.path.join(model_dir, name))]
        if missing:
            raise BackendRefused(
                "ecapa: model dir %s is missing %s; acquire weights via the user-approved "
                "download step first" % (model_dir, ", ".join(missing)))
        self.model_dir = model_dir
        self._model = None

    def file_hashes(self):
        out = {}
        for name in self.REQUIRED_FILES:
            digest = hashlib.sha256()
            with open(os.path.join(self.model_dir, name), "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            out[name] = digest.hexdigest()
        return out

    def _load(self):
        if self._model is None:
            try:
                import torch
                from speechbrain.inference.speaker import EncoderClassifier
            except ImportError as exc:
                raise BackendRefused("ecapa: speechbrain/torch not installed") from exc
            torch.manual_seed(0)
            torch.use_deterministic_algorithms(True)
            self._model = EncoderClassifier.from_hparams(
                source=self.model_dir, savedir=self.model_dir,
                run_opts={"device": "cpu"}, huggingface_cache_dir=self.model_dir)
        return self._model

    def embed(self, samples, sr):
        import torch
        model = self._load()
        if sr != 16000:
            raise BackendRefused("ecapa: expects 16 kHz mono input; resample upstream via ffmpeg")
        with torch.no_grad():
            tensor = torch.from_numpy(np.asarray(samples, dtype=np.float32)).unsqueeze(0)
            vector = model.encode_batch(tensor).squeeze().cpu().numpy()
        return _unit(vector)


def get_backend(name, model_dir=None):
    if name == "spectral-test":
        return SpectralTestBackend()
    if name == "ecapa":
        return EcapaBackend(model_dir)
    raise BackendRefused("unknown embedding backend: %r" % (name,))
