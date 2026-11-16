import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Anchor, PkState } from '../models';

@Component({
  selector: 'app-pk-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="pk" [class.done]="pk().finished">
      <div class="side left" [style.color]="a()?.color">{{ a()?.name }} · {{ scoreA() }}</div>
      <div class="center">
        @if (pk().finished) {
          <strong>{{ resultText() }}</strong>
        } @else {
          <span class="vs">VS</span> <span class="time">{{ pk().remaining }}s</span>
        }
      </div>
      <div class="side right" [style.color]="b()?.color">{{ scoreB() }} · {{ b()?.name }}</div>
      <div class="track">
        <div class="fill" [style.width.%]="ratio()" [style.background]="a()?.color"></div>
        <div class="rest" [style.background]="b()?.color"></div>
      </div>
    </div>
  `,
  styles: `
    .pk {
      display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 6px 12px;
      padding: 10px 16px; border-radius: 14px; background: #24253a;
    }
    .side { font-weight: 700; }
    .right { text-align: right; }
    .center { text-align: center; }
    .vs { font-weight: 900; letter-spacing: 2px; }
    .time { opacity: .8; margin-left: 6px; }
    .track { grid-column: 1 / -1; display: flex; height: 10px; border-radius: 6px; overflow: hidden; }
    .fill { transition: width .3s; }
    .rest { flex: 1; }
    .done { outline: 2px solid gold; }
  `,
})
export class PkBarComponent {
  readonly pk = input.required<PkState>();
  readonly anchors = input.required<Map<string, Anchor>>();

  readonly a = computed(() => this.anchors().get(this.pk().anchorA));
  readonly b = computed(() => this.anchors().get(this.pk().anchorB));
  readonly scoreA = computed(() => this.pk().scores[this.pk().anchorA] ?? 0);
  readonly scoreB = computed(() => this.pk().scores[this.pk().anchorB] ?? 0);
  readonly ratio = computed(() => {
    const total = this.scoreA() + this.scoreB();
    return total === 0 ? 50 : (this.scoreA() / total) * 100;
  });
  readonly resultText = computed(() => {
    const { winner, mvp } = this.pk();
    if (!winner) return 'Tie!';
    const name = this.anchors().get(winner)?.name ?? winner;
    return `${name} wins${mvp ? ` · MVP ${mvp}` : ''}`;
  });
}
