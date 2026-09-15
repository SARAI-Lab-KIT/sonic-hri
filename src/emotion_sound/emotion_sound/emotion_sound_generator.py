import os
import math
import time
import random
import pickle
from math import ceil
from copy import deepcopy

import rclpy
import numpy as np
import torch
import torchaudio
import soundfile as sf

from numpy.random import rand, randn
from numpy import asarray, sqrt, argsort
from rclpy.node import Node
from std_msgs.msg import String
from emotion_msgs.msg import EmotionState
import argparse
import pytorch_lightning as pl

import sys
sys.path.append("/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/clmr")
from clmr.models import SampleCNN
from clmr.modules import ContrastiveLearning
from clmr.utils import load_encoder_checkpoint, yaml_config_hook
from audiomentations import (
    Compose, PitchShift, HighPassFilter, LowPassFilter,
    TimeStretch, Gain, SevenBandParametricEQ
)

# ---------- PATHS ----------
SAMPLE_RATE = 44100
ENCODER_CHECKPOINT_PATH = "/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/clmr_magnatagatune_mlp/clmr_epoch=10000.ckpt"
CONFIG_PATH = "/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/clmr/config/config.yaml"
CLFR_PATH = "/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/clmr_clfr.pkl"
BLEEP_DIR = "/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/Bleep/Clean50dB_audio"
OUTPUT_DIR = "/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/transformed_audio_newclmr"

# ---------- CLMR + ES ----------
config = yaml_config_hook(CONFIG_PATH)
config['supervised'] = True
config['checkpoint_path'] = ENCODER_CHECKPOINT_PATH
config['seed'] = config.get('seed', 42)
config['accelerator'] = None
args = argparse.Namespace(**config)

pl.seed_everything(args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)

encoder = SampleCNN(strides=[3]*9, supervised=args.supervised, out_dim=6)
state_dict = load_encoder_checkpoint(args.checkpoint_path, 6)
encoder.load_state_dict(state_dict)
encoder.eval()

cl = ContrastiveLearning(args, encoder)
cl.eval()
cl.freeze()

with open(CLFR_PATH, 'rb') as f:
    classifier = pickle.load(f)

def loop_audio(signal, sr, max_duration_seconds):
    sig_len = len(signal)
    max_len = sr * max_duration_seconds
    looped_sig = deepcopy(signal)
    for _ in range(ceil(max_len / sig_len) - 1):
        looped_sig = np.concatenate((looped_sig, signal))
    return looped_sig[:max_len]


def get_clmr(signal):
    if not torch.is_tensor(signal):
        signal = torch.from_numpy(signal)
    if len(signal.shape) == 1:
        signal = signal.unsqueeze(0)
    if signal.shape[1] != 1:
        signal = signal.unsqueeze(1)
    return encoder(signal)


def get_clmr_va(clf, h0):
    va_dict = {
        0: np.array([-0.4, 0.8]),
        1: np.array([0.8, -0.58]),
        2: np.array([0.88, 0.36]),
        3: np.array([-0.82, -0.4]),
        4: np.array([0.7, 0.72]),
        5: np.array([0, -1])
    }
    w = clf.predict_proba(h0)[0]
    val = sum(w[i] * va_dict[i][0] for i in range(6))
    aro = sum(w[i] * va_dict[i][1] for i in range(6))
    return np.array([val, aro])


def augment(*params):
    return Compose([
        HighPassFilter(min_cutoff_freq=params[0], max_cutoff_freq=params[0], p=1),
        LowPassFilter(min_cutoff_freq=params[1], max_cutoff_freq=params[1], p=1),
        SevenBandParametricEQ(min_gain_db=params[2], max_gain_db=params[2], p=1),
        TimeStretch(min_rate=params[3], max_rate=params[3], p=1),
        PitchShift(min_semitones=params[4], max_semitones=params[4], p=1),
        Gain(min_gain_db=params[5], max_gain_db=params[5], p=1)
    ])


def transform_audio(audio_signal, sr, params):
    return augment(*params)(audio_signal, sr)


def in_bounds(point, bounds):
    return all(bounds[d, 0] <= point[d] <= bounds[d, 1] for d in range(len(bounds)))


def objective(audio_signal, sr, clmr_original, input_point, target_pc, classifier):
    transformed_signal = transform_audio(audio_signal, sr, input_point)
    looped_transformed_signal = loop_audio(transformed_signal, sr, 7)
    h = get_clmr(looped_transformed_signal)
    va_transformed = get_clmr_va(classifier, h)
    return np.sqrt(np.sum((va_transformed - target_pc) ** 2))


def es_plus(audio_signal, sr, target_va, mu=2, lam=4, n_iter=1):
    h0 = get_clmr(audio_signal)
    va_orig = get_clmr_va(classifier, h0)

    bounds = asarray([[1, 500], [600, 9000], [-24, 24],
                      [0.7, 1.5], [-8, 8], [-9, 9]])
    step_size = asarray([sqrt((b[1] - b[0]) / 5) for b in bounds])

    best, best_eval = None, 1e+10
    population = [bounds[:, 0] + rand(len(bounds)) *
                  (bounds[:, 1] - bounds[:, 0]) for _ in range(lam)]

    all_transforms = []
    all_scores = []

    for _ in range(n_iter):
        scores = [objective(audio_signal, sr, va_orig, c,
                            target_va, classifier) for c in population]
        all_scores.extend(scores)
        all_transforms.extend(population)

        ranks = argsort(argsort(scores))
        selected = [i for i, r in enumerate(ranks) if r < mu]
        children = []
        for i in selected:
            if scores[i] < best_eval and scores[i] >= 0.1:
                best, best_eval = population[i], scores[i]
            children.append(population[i])
            for _ in range(int(lam / mu)):
                child = None
                while child is None or not in_bounds(child, bounds):
                    child = population[i] + randn(len(bounds)) * step_size
                children.append(child)
        population = children

    return best, best_eval, all_transforms, all_scores


# ---------- ROS2 ----------
class EmotionSoundGenerator(Node):
    def __init__(self):
        super().__init__('emotion_sound_generator')

        self.declare_parameter("mu", 5)
        self.declare_parameter("lam", 5)
        self.declare_parameter("n_iter", 1)

        self.latest_valence = None
        self.latest_arousal = None
        self.latest_source_folder = None

        self.subscription_va = self.create_subscription(
            EmotionState, '/emotion_target', self.va_callback, 10)
        self.subscription_sf = self.create_subscription(
            EmotionState, '/closest_emotion_detection', self.sf_callback, 10)
        self.publisher_ = self.create_publisher(String, '/emotion_sound', 10)

    def va_callback(self, msg):
        self.latest_valence = msg.valence
        self.latest_arousal = msg.arousal
        self.get_logger().info(
            f"Received valence: {msg.valence}, arousal: {msg.arousal}")
        self.try_process()

    def sf_callback(self, msg):
        self.latest_source_folder = msg.source_folder
        self.get_logger().info(f"source_folder: {msg.source_folder}")
        self.try_process()

    def try_process(self):
        if (self.latest_valence is None or
                self.latest_arousal is None or
                self.latest_source_folder is None):
            self.get_logger().info("waiting for inputs")
            return

        try:
            start_time = time.time()

            folder = self.latest_source_folder
            target_va = np.array(
                [self.latest_valence, self.latest_arousal])
            self.get_logger().info(f"Target VA: {target_va}")

            folder_path = os.path.join(BLEEP_DIR, folder)
            files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]
            if not files:
                self.get_logger().warn(f"No .wav files found in {folder_path}")
                return

            input_audio = os.path.join(folder_path, random.choice(files))
            signal, sr = torchaudio.load(input_audio)
            looped_signal = loop_audio(signal[0].numpy(), sr, 7)

            mu = int(self.get_parameter("mu").value)
            lam = int(self.get_parameter("lam").value)
            n_iter = int(self.get_parameter("n_iter").value)
            self.get_logger().info(
                f"ES params: mu={mu}, lam={lam}, n_iter={n_iter}")

            filename_base = os.path.splitext(
                os.path.basename(input_audio))[0]
            out_folder = os.path.join(
                OUTPUT_DIR, folder + f"_V{target_va[0]:.2f}_A{target_va[1]:.2f}")
            os.makedirs(out_folder, exist_ok=True)

            best, best_eval, all_transforms, all_scores = es_plus(
                looped_signal, sr, target_va, mu=mu, lam=lam, n_iter=n_iter)

            top_k = min(5, len(all_scores))
            top_k_indices = np.argsort(all_scores)[:top_k]
            top_k_transforms = [all_transforms[i]
                                for i in top_k_indices]

            va_results = []
            for transform in top_k_transforms:
                transformed_signal = transform_audio(
                    signal[0].numpy(), sr, transform)
                looped = loop_audio(transformed_signal, sr, 7)
                h = get_clmr(looped)
                va = get_clmr_va(classifier, h)
                dist = np.linalg.norm(va - target_va)
                va_results.append((transform, transformed_signal, va, dist))

            va_results.sort(key=lambda x: x[3])

            for i, (transform, signal_out, va, dist) in enumerate(va_results):
                filename = (f"{filename_base}_best.wav" if i == 0
                            else f"{filename_base}_rank{i + 1}.wav")
                out_path = os.path.join(out_folder, filename)
                sf.write(out_path, signal_out, sr)
                if i == 0:
                    best_out_path = out_path

            result_msg = String()
            result_msg.data = f"New sound saved to: {best_out_path}"
            self.publisher_.publish(result_msg)
            self.get_logger().info(
                f"Published new sound on /emotion_sound: {result_msg.data}")

            end_time = time.time()
            elapsed = end_time - start_time
            self.get_logger().info(f"Processing time: {elapsed:.2f} seconds")

        except Exception as e:
            self.get_logger().error(f"Error in try_process: {e}")

        self.latest_valence = None
        self.latest_arousal = None
        self.latest_source_folder = None


def main(args=None):
    rclpy.init(args=args)
    node = EmotionSoundGenerator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
