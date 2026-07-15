import { Loader2, Pause, Play, SkipBack, SkipForward } from "lucide-react";

import type { Sentence } from "../types";

type PlayerBarProps = {
  currentSentence: Sentence | null;
  isGeneratingAudio: boolean;
  isPlaying: boolean;
  onMoveSentence: (offset: number) => void;
  onTogglePlayback: () => void;
};

export function PlayerBar({
  currentSentence,
  isGeneratingAudio,
  isPlaying,
  onMoveSentence,
  onTogglePlayback
}: PlayerBarProps) {
  return (
    <footer className="player-bar">
      <button
        aria-label="上一句"
        data-testid="previous-sentence"
        onClick={() => onMoveSentence(-1)}
        type="button"
      >
        <SkipBack size={20} />
      </button>
      <button
        aria-label={isPlaying ? "暂停" : "播放"}
        className="primary-control"
        data-testid="play-toggle"
        disabled={isGeneratingAudio}
        onClick={onTogglePlayback}
        type="button"
      >
        {isGeneratingAudio ? (
          <Loader2 className="spin" size={22} />
        ) : isPlaying ? (
          <Pause size={22} />
        ) : (
          <Play size={22} />
        )}
      </button>
      <button
        aria-label="下一句"
        data-testid="next-sentence"
        onClick={() => onMoveSentence(1)}
        type="button"
      >
        <SkipForward size={20} />
      </button>
      <div className="now-playing">
        <span>当前句</span>
        <strong>{currentSentence?.text ?? "未选择"}</strong>
      </div>
    </footer>
  );
}
