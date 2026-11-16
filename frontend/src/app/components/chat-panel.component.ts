import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FeedItem } from '../models';

@Component({
  selector: 'app-chat-panel',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- column-reverse keeps the newest message pinned to the bottom -->
    <ul class="feed">
      @for (item of reversed(); track item.id) {
        <li [class]="item.kind">
          @if (item.who) {
            <span class="who" [style.color]="item.color">{{ item.who }}</span>
          }
          <span class="text">{{ item.text }}</span>
        </li>
      }
    </ul>
    <form class="input" (ngSubmit)="submit()">
      <input
        name="draft"
        [ngModel]="draft()"
        (ngModelChange)="draft.set($event)"
        maxlength="100"
        placeholder="Say something... (mention a host by name to get their reply)"
        autocomplete="off"
      />
      <button type="submit" [disabled]="!draft().trim()">Send</button>
    </form>
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-height: 0; flex: 1; }
    .feed {
      flex: 1; min-height: 0; overflow-y: auto; margin: 0; padding: 8px; list-style: none;
      display: flex; flex-direction: column-reverse; gap: 6px;
    }
    li { font-size: 14px; line-height: 1.45; word-break: break-word; }
    .who { font-weight: 700; margin-right: 6px; }
    .chat .who { color: #9fb4ff; }
    .gift { color: #ffd166; }
    .gift .who { color: #ffd166; }
    .system { opacity: .6; font-size: 12px; }
    .error { color: #ff6b6b; }
    .input { display: flex; gap: 6px; padding: 8px; border-top: 1px solid #2c2d40; }
    input {
      flex: 1; padding: 8px 10px; border-radius: 10px; border: 1px solid #3a3b55;
      background: #12131c; color: inherit;
    }
    button {
      padding: 8px 14px; border-radius: 10px; border: 0; background: #ff6b9d; color: #111;
      font-weight: 700; cursor: pointer;
    }
    button:disabled { opacity: .4; cursor: default; }
  `,
})
export class ChatPanelComponent {
  readonly feed = input.required<FeedItem[]>();
  readonly send = output<string>();
  readonly draft = signal('');
  readonly reversed = computed(() => [...this.feed()].reverse());

  submit(): void {
    const text = this.draft().trim();
    if (!text) return;
    this.send.emit(text);
    this.draft.set('');
  }
}
