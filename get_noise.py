"""
Collect silent parts of audio for a noise profile
Segment wav and sort them by loudness, measured by FFT and A_weighting
h2kyeong, 2025. 9. 26.
"""

import numpy as np
import soundfile as sf
import librosa

import os

def save_gated_silent_segments_corrected(
	audio_path, 
	output_path, 
	target_sr=48000, 
	block_duration_ms=400, 
	overlap_ratio=0.75, 
	gating_threshold_db=-15.0
):
	if not os.path.exists(audio_path):
		raise FileNotFoundError(f"Input audio file not found at: {audio_path}")
	
	y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
	
	# 1. STFT Parameters
	n_fft = int(target_sr * (block_duration_ms / 1000.0))
	hop_length = int(n_fft * (1.0 - overlap_ratio))
	
	# 2. Calculate A-Weighting Filter (Frequency Domain)
	
	# a. Generate the array of frequency bins (in Hz)
	# librosa.fft_frequencies returns the frequencies corresponding to the STFT output.
	fft_freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
	
	# b. Calculate the A-weighting gain in dB for each frequency bin
	a_weighting_db = librosa.A_weighting(fft_freqs)
	
	# c. Convert the dB gains to linear amplitude scaling factors
	# This filter is 1D: (frequency_bins,)
	a_weighting_linear = librosa.db_to_amplitude(a_weighting_db)
	
	# 3. Calculate STFT and Power Spectrum
	D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
	D_mag = np.abs(D)
	
	# 4. Apply Weighting and Calculate Segment Loudness

	# Apply the linear A-weighting filter to the magnitude spectrum (2D: freq, frames)
	D_weighted_mag = D_mag * a_weighting_linear[:, np.newaxis]

	# Convert weighted magnitude back to power
	D_weighted_power = D_weighted_mag**2

	# Sum the weighted power across all frequency bins (axis=0) to get total power per frame
	weighted_power_sum = np.sum(D_weighted_power, axis=0)

	# For an unwindowed STFT, the power scaling factor is 1/N_FFT.
	normalization_factor = n_fft

	# Divide by the factor and convert to dB (10 * log10(Power / 1.0))
	loudness_segments_db = 10 * np.log10(
		(weighted_power_sum / normalization_factor) + np.finfo(np.float32).eps
	)
	silent_indices = list(range(len(loudness_segments_db)))
	silent_indices.sort(key=loudness_segments_db.__getitem__)
	
	for i in range(len(loudness_segments_db)):
		if loudness_segments_db[silent_indices[i]] > -10.0: break
	silent_indices = silent_indices[:i]
	
	# 5. Extract and Concatenate Silent Frames from the ORIGINAL Signal (y)
	y_silent = []
	
	for i in silent_indices:
		start_sample = i * hop_length
		end_sample = start_sample + n_fft
		
		# Boundary check for the last frame
		segment = y[start_sample:end_sample]
		if len(segment) < n_fft:
			segment = np.pad(segment, (0, n_fft - len(segment)))
			
		y_silent.append(segment)

	y_silent_concatenated = np.concatenate(y_silent)
	
	# 6. Save the Result to a WAV File
	sf.write(output_path, y_silent_concatenated, sr)
	
	print(f"\nSuccessfully saved {len(silent_indices)} silent segments to: {output_path}")
	print(f"Total duration of saved audio: {len(y_silent_concatenated) / sr:.2f} seconds (includes overlap/padding)")

save_gated_silent_segments_corrected('a.wav', 'noise.wav')
