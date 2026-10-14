import { useSoundStore } from './useSoundStore';

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioCtx) {
    const AudioContextClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

/**
 * Play a gentle micro-pop on file drop (sine wave 400 Hz -> 800 Hz, fast attack, 40 ms decay, volume 0.05).
 */
export function playDropBlip(): void {
  if (useSoundStore.getState().isMuted) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(400, now);
  osc.frequency.exponentialRampToValueAtTime(800, now + 0.04);

  gain.gain.setValueAtTime(0.05, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.04);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.045);
}

/**
 * Play a calm muted dual-chime upon note persistence confirmation (80 ms).
 */
export function playSuccessChime(): void {
  if (useSoundStore.getState().isMuted) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;

  // Harmonique 1 (587.33 Hz - Ré5)
  const osc1 = ctx.createOscillator();
  const gain1 = ctx.createGain();
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(587.33, now);
  gain1.gain.setValueAtTime(0.04, now);
  gain1.gain.exponentialRampToValueAtTime(0.0001, now + 0.06);
  osc1.connect(gain1);
  gain1.connect(ctx.destination);
  osc1.start(now);
  osc1.stop(now + 0.065);

  // Harmonique 2 (880 Hz - La5)
  const osc2 = ctx.createOscillator();
  const gain2 = ctx.createGain();
  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(880, now + 0.03);
  gain2.gain.setValueAtTime(0.0001, now);
  gain2.gain.setValueAtTime(0.04, now + 0.03);
  gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.08);
  osc2.connect(gain2);
  gain2.connect(ctx.destination);
  osc2.start(now + 0.03);
  osc2.stop(now + 0.085);
}

/**
 * Play a low-frequency muted thud on error (sine wave 140 Hz -> 70 Hz, 60 ms).
 */
export function playErrorThud(): void {
  if (useSoundStore.getState().isMuted) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(140, now);
  osc.frequency.exponentialRampToValueAtTime(70, now + 0.06);

  gain.gain.setValueAtTime(0.06, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.06);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.065);
}
