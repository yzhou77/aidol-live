import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';

import { Anchor, Gift } from '../models';

export interface GiftRequest {
  giftId: string;
  count: number;
}

@Component({
  selector: 'app-gift-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="bar">
      <div class="target">
        Send to:
        @if (target(); as t) {
          <strong [style.color]="t.color">{{ t.name }}</strong>
        } @else {
          <em>click an anchor above</em>
        }
        <span class="coins">💰 {{ coins() }} coins</span>
      </div>
      <div class="gifts">
        @for (g of gifts(); track g.id) {
          <button
            type="button"
            [disabled]="!target() || g.value * count() > coins()"
            (click)="send.emit({ giftId: g.id, count: count() })"
            [title]="g.name + ' · ' + g.value + ' coins'"
          >
            <span class="emoji">{{ g.emoji }}</span>
            <span class="label">{{ g.name }}</span>
            <span class="price">{{ g.value }}</span>
          </button>
        }
        <select [value]="count()" (change)="count.set(+$any($event.target).value)" aria-label="Quantity">
          @for (n of counts; track n) {
            <option [value]="n">×{{ n }}</option>
          }
        </select>
      </div>
    </div>
  `,
  styles: `
    .bar { display: flex; flex-direction: column; gap: 8px; }
    .target { font-size: 14px; display: flex; gap: 8px; align-items: center; }
    .coins { margin-left: auto; color: #ffd166; }
    .gifts { display: flex; flex-wrap: wrap; gap: 8px; align-items: stretch; }
    button {
      display: flex; flex-direction: column; align-items: center; min-width: 64px; padding: 6px 8px;
      border-radius: 12px; border: 1px solid #3a3b55; background: #1c1d2b; color: inherit; cursor: pointer;
    }
    button:hover:not(:disabled) { border-color: #ffd166; }
    button:disabled { opacity: .35; cursor: default; }
    .emoji { font-size: 22px; }
    .label { font-size: 12px; }
    .price { font-size: 11px; opacity: .6; }
    select {
      border-radius: 10px; background: #1c1d2b; color: inherit; border: 1px solid #3a3b55; padding: 0 8px;
    }
  `,
})
export class GiftBarComponent {
  readonly gifts = input.required<Gift[]>();
  readonly target = input<Anchor | null>(null);
  readonly coins = input(0);
  readonly send = output<GiftRequest>();

  readonly counts = [1, 5, 10, 66];
  readonly count = signal(1);
}
