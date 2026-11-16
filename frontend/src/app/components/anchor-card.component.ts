import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Anchor } from '../models';

@Component({
  selector: 'app-anchor-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      type="button"
      class="card"
      [class.selected]="selected()"
      [class.speaking]="speaking()"
      [style.--accent]="anchor().color"
      (click)="pick.emit(anchor().id)"
      [attr.aria-label]="'Select anchor ' + anchor().name"
    >
      @if (bubble()) {
        <div class="bubble">{{ bubble() }}</div>
      }
      <svg class="avatar" viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r="56" class="halo" />
        <circle cx="60" cy="62" r="40" class="face" />
        <circle cx="46" cy="56" r="5" class="eye" />
        <circle cx="74" cy="56" r="5" class="eye" />
        <ellipse cx="60" cy="78" rx="10" ry="4" class="mouth" [class.talking]="speaking()" />
      </svg>
      <div class="name">
        {{ anchor().name }} <span class="ai-tag">AI</span>
      </div>
      <div class="talent">Talent: {{ anchor().talent }}</div>
      <div class="stats">
        <span>🔥 {{ popularity() }}</span>
        @if (pkScore() !== null) {
          <span class="pk">PK {{ pkScore() }}</span>
        }
      </div>
    </button>
  `,
  styles: `
    :host { display: block; }
    .card {
      position: relative; width: 100%; padding: 16px 12px 12px; border-radius: 16px;
      background: #1c1d2b; border: 2px solid transparent; color: inherit; cursor: pointer;
      display: flex; flex-direction: column; align-items: center; gap: 6px; font: inherit;
      transition: transform .15s, border-color .15s;
    }
    .card:hover { transform: translateY(-2px); }
    .card.selected { border-color: var(--accent); }
    .card.speaking { box-shadow: 0 0 24px -4px var(--accent); }
    .avatar { width: 96px; height: 96px; }
    .halo { fill: none; stroke: var(--accent); stroke-width: 3; opacity: .35; }
    .speaking .halo { opacity: 1; animation: pulse 1s ease-in-out infinite; transform-origin: center; }
    .face { fill: var(--accent); }
    .eye { fill: #1c1d2b; }
    .mouth { fill: #1c1d2b; transform-box: fill-box; transform-origin: center; }
    .mouth.talking { animation: talk .25s ease-in-out infinite alternate; }
    .name { font-weight: 700; font-size: 18px; }
    .ai-tag {
      font-size: 11px; padding: 1px 6px; border-radius: 6px; vertical-align: middle;
      background: var(--accent); color: #111;
    }
    .talent { font-size: 12px; opacity: .7; }
    .stats { display: flex; gap: 10px; font-size: 13px; }
    .pk { color: var(--accent); font-weight: 700; }
    .bubble {
      position: absolute; bottom: calc(100% - 8px); left: 8px; right: 8px; z-index: 2;
      background: #fff; color: #222; border-radius: 12px; padding: 8px 10px; font-size: 13px;
      line-height: 1.4; box-shadow: 0 6px 20px rgba(0,0,0,.35);
    }
    @keyframes talk { from { transform: scaleY(.6); } to { transform: scaleY(2.4); } }
    @keyframes pulse { 50% { stroke-width: 6; } }
  `,
})
export class AnchorCardComponent {
  readonly anchor = input.required<Anchor>();
  readonly bubble = input<string | undefined>(undefined);
  readonly speaking = input(false);
  readonly popularity = input(0);
  readonly pkScore = input<number | null>(null);
  readonly selected = input(false);
  readonly pick = output<string>();
}
