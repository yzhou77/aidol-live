import { Injectable, signal } from '@angular/core';

import { VoiceStyle } from '../models';

const MAX_QUEUE = 4; // beyond this, show the bubble silently instead of piling up audio

/**
 * Browser text-to-speech via the Web Speech API (free, no server cost).
 * Falls back to timed "silent" bubbles when TTS is off or unsupported.
 */
@Injectable({ providedIn: 'root' })
export class SpeechService {
  readonly supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  readonly enabled = signal(this.supported);

  private voice?: SpeechSynthesisVoice;
  private queued = 0;

  constructor() {
    if (!this.supported) return;
    const pick = () => {
      this.voice = window.speechSynthesis
        .getVoices()
        .find((v) => v.lang.toLowerCase().startsWith('en'));
    };
    pick();
    window.speechSynthesis.addEventListener('voiceschanged', pick);
  }

  toggle(): void {
    this.enabled.update((on) => !on);
    if (!this.enabled() && this.supported) {
      window.speechSynthesis.cancel();
      this.queued = 0;
    }
  }

  say(text: string, style: VoiceStyle | undefined, onStart: () => void, onEnd: () => void): void {
    if (!this.supported || !this.enabled() || this.queued >= MAX_QUEUE) {
      onStart();
      setTimeout(onEnd, Math.min(9000, 1500 + text.length * 150));
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text.replace(/~/g, ''));
    utterance.lang = 'en-US';
    if (this.voice) utterance.voice = this.voice;
    utterance.pitch = clamp(style?.pitch ?? 1, 0, 2);
    utterance.rate = clamp(style?.rate ?? 1, 0.5, 2);

    this.queued++;
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      this.queued = Math.max(0, this.queued - 1);
      onEnd();
    };
    utterance.onstart = onStart;
    utterance.onend = finish;
    utterance.onerror = finish;
    window.speechSynthesis.speak(utterance);
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
