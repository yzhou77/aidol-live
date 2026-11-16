export interface VoiceStyle {
  pitch: number;
  rate: number;
}

export interface Anchor {
  id: string;
  name: string;
  talent: string;
  catchphrase: string;
  color: string;
  voice: VoiceStyle;
}

export interface Gift {
  id: string;
  name: string;
  emoji: string;
  value: number;
}

export interface Me {
  name: string;
  coins: number;
  totalSpent: number;
  visits: number;
}

export interface PkState {
  anchorA: string;
  anchorB: string;
  scores: Record<string, number>;
  remaining: number;
  duration: number;
  finished: boolean;
  winner?: string | null;
  mvp?: string | null;
}

export interface LeaderboardItem {
  name: string;
  total: number;
}

export type FeedKind = 'chat' | 'system' | 'speech' | 'gift' | 'error';

export interface FeedItem {
  id: number;
  kind: FeedKind;
  who?: string;
  color?: string;
  text: string;
}

/** Events pushed by the backend over the WebSocket. */
export type ServerEvent =
  | {
      type: 'state';
      roomId: string;
      anchors: Anchor[];
      gifts: Gift[];
      pk: PkState | null;
      viewers: number;
      popularity: Record<string, number>;
      leaderboard: LeaderboardItem[];
      you?: Me;
    }
  | { type: 'system'; text: string }
  | { type: 'viewers'; count: number }
  | { type: 'chat'; fan: string; text: string }
  | { type: 'speech'; anchorId: string; kind: string; text: string }
  | {
      type: 'gift';
      fan: string;
      anchorId: string;
      giftId: string;
      count: number;
      value: number;
      popularity: number;
    }
  | { type: 'wallet'; coins: number }
  | { type: 'leaderboard'; items: LeaderboardItem[] }
  | ({ type: 'pk' } & PkState)
  | ({ type: 'pk_end' } & PkState)
  | { type: 'error'; message: string };
