import { Injectable, computed, inject, signal } from '@angular/core';

import {
  Anchor,
  FeedItem,
  FeedKind,
  Gift,
  LeaderboardItem,
  Me,
  PkState,
  ServerEvent,
} from '../models';
import { SpeechService } from './speech.service';

export type RoomStatus = 'idle' | 'connecting' | 'live' | 'closed';

const FEED_LIMIT = 150;
const PK_RESULT_MS = 8000;

/** Owns the WebSocket connection and exposes room state as signals. */
@Injectable({ providedIn: 'root' })
export class LiveRoomService {
  private readonly speech = inject(SpeechService);
  private socket?: WebSocket;
  private nextFeedId = 1;
  private pkClearTimer?: ReturnType<typeof setTimeout>;

  readonly status = signal<RoomStatus>('idle');
  readonly lastError = signal<string | null>(null);
  readonly me = signal<Me | null>(null);
  readonly anchors = signal<Anchor[]>([]);
  readonly gifts = signal<Gift[]>([]);
  readonly pk = signal<PkState | null>(null);
  readonly viewers = signal(0);
  readonly popularity = signal<Record<string, number>>({});
  readonly leaderboard = signal<LeaderboardItem[]>([]);
  readonly feed = signal<FeedItem[]>([]);
  /** Current speech bubble per anchor id. */
  readonly bubbles = signal<Record<string, string>>({});
  readonly speakingId = signal<string | null>(null);

  readonly anchorById = computed(() => new Map(this.anchors().map((a) => [a.id, a])));
  readonly giftById = computed(() => new Map(this.gifts().map((g) => [g.id, g])));

  join(nickname: string, roomId = 'main'): void {
    this.socket?.close();
    this.lastError.set(null);
    this.status.set('connecting');

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/rooms/${roomId}`);
    this.socket = ws;
    ws.onopen = () => this.send({ type: 'join', fan: nickname });
    ws.onmessage = (msg) => this.handle(JSON.parse(msg.data) as ServerEvent);
    ws.onclose = () => {
      if (this.socket === ws) this.status.set('closed');
    };
  }

  sendChat(text: string): void {
    const trimmed = text.trim();
    if (trimmed) this.send({ type: 'chat', text: trimmed });
  }

  sendGift(anchorId: string, giftId: string, count: number): void {
    this.send({ type: 'gift', anchorId, giftId, count });
  }

  startPk(anchorA: string, anchorB: string): void {
    this.send({ type: 'start_pk', anchorA, anchorB });
  }

  private send(payload: Record<string, unknown>): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  private handle(e: ServerEvent): void {
    switch (e.type) {
      case 'state':
        this.anchors.set(e.anchors);
        this.gifts.set(e.gifts);
        this.pk.set(e.pk);
        this.viewers.set(e.viewers);
        this.popularity.set(e.popularity);
        this.leaderboard.set(e.leaderboard);
        if (e.you) this.me.set(e.you);
        this.status.set('live');
        break;
      case 'system':
        this.push('system', e.text);
        break;
      case 'viewers':
        this.viewers.set(e.count);
        break;
      case 'chat':
        this.push('chat', e.text, e.fan);
        break;
      case 'speech': {
        const anchor = this.anchorById().get(e.anchorId);
        this.push('speech', e.text, anchor?.name ?? e.anchorId, anchor?.color);
        this.say(e.anchorId, e.text);
        break;
      }
      case 'gift': {
        const anchor = this.anchorById().get(e.anchorId);
        const gift = this.giftById().get(e.giftId);
        this.popularity.update((p) => ({ ...p, [e.anchorId]: e.popularity }));
        this.push(
          'gift',
          `sent ${anchor?.name ?? e.anchorId} ${gift?.emoji ?? '🎁'}${gift?.name ?? e.giftId} ×${e.count}`,
          e.fan,
        );
        break;
      }
      case 'wallet':
        this.me.update((m) => (m ? { ...m, coins: e.coins } : m));
        break;
      case 'leaderboard':
        this.leaderboard.set(e.items);
        break;
      case 'pk': {
        clearTimeout(this.pkClearTimer);
        const { type: _type, ...state } = e;
        this.pk.set(state);
        break;
      }
      case 'pk_end': {
        const { type: _type, ...state } = e;
        this.pk.set(state);
        const names = this.anchorById();
        this.push(
          'system',
          state.winner
            ? `PK over: ${names.get(state.winner)?.name ?? state.winner} wins!` +
                (state.mvp ? ` MVP: ${state.mvp}` : '')
            : 'PK over: it is a tie!',
        );
        clearTimeout(this.pkClearTimer);
        this.pkClearTimer = setTimeout(() => this.pk.set(null), PK_RESULT_MS);
        break;
      }
      case 'error':
        this.lastError.set(e.message);
        this.push('error', e.message);
        break;
    }
  }

  private say(anchorId: string, text: string): void {
    const anchor = this.anchorById().get(anchorId);
    this.speech.say(
      text,
      anchor?.voice,
      () => {
        this.bubbles.update((b) => ({ ...b, [anchorId]: text }));
        this.speakingId.set(anchorId);
      },
      () => {
        this.bubbles.update((b) => {
          if (b[anchorId] !== text) return b;
          const { [anchorId]: _gone, ...rest } = b;
          return rest;
        });
        if (this.speakingId() === anchorId) this.speakingId.set(null);
      },
    );
  }

  private push(kind: FeedKind, text: string, who?: string, color?: string): void {
    const item: FeedItem = { id: this.nextFeedId++, kind, text, who, color };
    this.feed.update((items) => [...items, item].slice(-FEED_LIMIT));
  }
}
