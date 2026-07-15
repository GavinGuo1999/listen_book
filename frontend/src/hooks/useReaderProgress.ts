import type { RefObject } from "react";
import { useEffect, useRef } from "react";

import { fetchBookProgress, saveBookProgress } from "../api";
import type { Sentence } from "../types";

const PROGRESS_SAVE_INTERVAL_MS = 5000;

type RestoredPlaybackPosition = {
  sentenceId: string;
  audioPositionMs: number;
};

export function useReaderProgress(
  bookId: string | null,
  sentenceId: string | null,
  isPlaying: boolean,
  audioRef: RefObject<HTMLAudioElement>
) {
  const restoredPositionRef = useRef<RestoredPlaybackPosition | null>(null);

  function getAudioPositionMs() {
    const audio = audioRef.current;
    if (!audio || !Number.isFinite(audio.currentTime)) {
      return 0;
    }
    return Math.max(0, Math.round(audio.currentTime * 1000));
  }

  function save(nextSentenceId: string | null, audioPositionMs = 0) {
    if (!bookId) {
      return;
    }
    saveBookProgress(bookId, nextSentenceId, audioPositionMs).catch(() => {
      // Progress persistence must not interrupt reading or playback.
    });
  }

  async function restore(targetBookId: string, sentences: Sentence[]) {
    if (!targetBookId) {
      restoredPositionRef.current = null;
      return null;
    }
    try {
      const progress = await fetchBookProgress(targetBookId);
      const savedSentence = sentences.find((sentence) => sentence.id === progress?.sentence_id);
      if (!savedSentence) {
        restoredPositionRef.current = null;
        return null;
      }
      restoredPositionRef.current = {
        sentenceId: savedSentence.id,
        audioPositionMs: progress?.audio_position_ms ?? 0
      };
      return savedSentence.id;
    } catch {
      restoredPositionRef.current = null;
      return null;
    }
  }

  function getResumePositionMs(nextSentenceId: string) {
    return restoredPositionRef.current?.sentenceId === nextSentenceId
      ? restoredPositionRef.current.audioPositionMs
      : 0;
  }

  function clearRestoredPosition() {
    restoredPositionRef.current = null;
  }

  useEffect(() => {
    if (!isPlaying || !sentenceId || !bookId) {
      return;
    }
    const intervalId = window.setInterval(() => {
      save(sentenceId, getAudioPositionMs());
    }, PROGRESS_SAVE_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [bookId, isPlaying, sentenceId]);

  return {
    clearRestoredPosition,
    getAudioPositionMs,
    getResumePositionMs,
    restore,
    save
  };
}
