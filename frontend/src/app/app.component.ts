import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AnchorCardComponent } from './components/anchor-card.component';
import { ChatPanelComponent } from './components/chat-panel.component';
import { GiftBarComponent, GiftRequest } from './components/gift-bar.component';
import { PkBarComponent } from './components/pk-bar.component';
import { LiveRoomService } from './services/live-room.service';
import { SpeechService } from './services/speech.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, AnchorCardComponent, ChatPanelComponent, GiftBarComponent, PkBarComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  readonly room = inject(LiveRoomService);
  readonly speech = inject(SpeechService);

  readonly nickname = signal('');
  readonly selected = signal<string | null>(null);
  readonly pkA = signal('');
  readonly pkB = signal('');

  /** Gift target: the clicked anchor, defaulting to the first one. */
  readonly targetId = computed(() => this.selected() ?? this.room.anchors()[0]?.id ?? null);
  readonly target = computed(() => this.room.anchorById().get(this.targetId() ?? '') ?? null);
  readonly canStartPk = computed(
    () => !!this.pkA() && !!this.pkB() && this.pkA() !== this.pkB() && !this.room.pk(),
  );

  enter(): void {
    const name = this.nickname().trim();
    if (name) this.room.join(name);
  }

  pkScore(anchorId: string): number | null {
    const pk = this.room.pk();
    return pk && anchorId in pk.scores ? pk.scores[anchorId] : null;
  }

  sendGift(req: GiftRequest): void {
    const id = this.targetId();
    if (id) this.room.sendGift(id, req.giftId, req.count);
  }

  startPk(): void {
    if (this.canStartPk()) this.room.startPk(this.pkA(), this.pkB());
  }
}
