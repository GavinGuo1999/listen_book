import type { Dispatch, SetStateAction } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  fetchChapters,
  fetchSentenceAudioStatuses,
  generateSentenceAudio,
  prefetchChapterAudio,
  prefetchSentenceAudio
} from "../api";
import type { AudioAsset, BookSummary, Chapter, Sentence } from "../types";
import { useReaderProgress } from "./useReaderProgress";

const INITIAL_PREFETCH_SENTENCE_COUNT = 5;
const PLAYBACK_PREFETCH_SENTENCE_COUNT = 8;
const AUDIO_STATUS_POLL_INTERVAL_MS = 2500;
const AUDIO_READY_POLL_INTERVAL_MS = 750;
const AUDIO_READY_MAX_POLLS = 80;
type SetError = Dispatch<SetStateAction<string | null>>;

export function useAudioPlayer(setError: SetError) {
  const [selectedBookId, setSelectedBookId] = useState<string | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentSentenceId, setCurrentSentenceId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);
  const [activePrefetchChapterId, setActivePrefetchChapterId] = useState<string | null>(null);
  const [audioAssetsBySentenceId, setAudioAssetsBySentenceId] = useState<
    Record<string, AudioAsset>
  >({});
  const [prefetchingSentenceIds, setPrefetchingSentenceIds] = useState<Set<string>>(
    () => new Set()
  );
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioCacheRef = useRef<Map<string, Promise<AudioAsset>>>(new Map());
  const audioPreloadRef = useRef<Map<string, HTMLAudioElement>>(new Map());
  const prefetchingSentenceIdsRef = useRef<Set<string>>(new Set());
  const progress = useReaderProgress(selectedBookId, currentSentenceId, isPlaying, audioRef);

  const flatSentences = useMemo(
    () => chapters.flatMap((chapter) => chapter.paragraphs.flatMap((p) => p.sentences)),
    [chapters]
  );
  const currentSentence =
    flatSentences.find((sentence) => sentence.id === currentSentenceId) ?? null;

  function resetContentState() {
    audioRef.current?.pause();
    if (audioRef.current) {
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
    setCurrentSentenceId(null);
    setIsPlaying(false);
    setIsGeneratingAudio(false);
    setChapters([]);
    setAudioAssetsBySentenceId({});
    setPrefetchingSentenceIds(new Set());
    setActivePrefetchChapterId(null);
    audioCacheRef.current.clear();
    audioPreloadRef.current.clear();
    prefetchingSentenceIdsRef.current.clear();
    progress.clearRestoredPosition();
  }

  function clear() {
    resetContentState();
    setSelectedBookId(null);
  }

  function selectUploadedBook(book: BookSummary) {
    resetContentState();
    setSelectedBookId(book.id);
  }

  async function selectBook(book: BookSummary) {
    resetContentState();
    setSelectedBookId(book.id);
    if (book.status === "ready") {
      await loadChapters(book.id);
    }
  }

  async function loadChapters(bookId: string) {
    setIsLoadingChapters(true);
    setError(null);
    try {
      const nextChapters = await fetchChapters(bookId);
      setChapters(nextChapters);
      const sentences = nextChapters.flatMap((chapter) =>
        chapter.paragraphs.flatMap((paragraph) => paragraph.sentences)
      );
      const restoredSentenceId = await progress.restore(bookId, sentences);
      if (restoredSentenceId) {
        setCurrentSentenceId(restoredSentenceId);
      }
      void prefetchSentences(sentences.slice(0, INITIAL_PREFETCH_SENTENCE_COUNT));
    } catch (error) {
      setError(error instanceof Error ? error.message : "加载正文失败");
      setChapters([]);
    } finally {
      setIsLoadingChapters(false);
    }
  }

  function warmBrowserAudio(audio: AudioAsset) {
    if (!audio.audio_url || audioPreloadRef.current.has(audio.sentence_id)) {
      return;
    }
    const preloadAudio = new Audio(audio.audio_url);
    preloadAudio.preload = "auto";
    preloadAudio.load();
    audioPreloadRef.current.set(audio.sentence_id, preloadAudio);
  }

  function rememberAudioAssets(assets: AudioAsset[]) {
    if (assets.length === 0) {
      return;
    }
    assets.forEach(warmBrowserAudio);
    setAudioAssetsBySentenceId((current) => {
      const next = { ...current };
      assets.forEach((audio) => {
        next[audio.sentence_id] = audio;
      });
      return next;
    });
  }

  function setPrefetching(sentenceIds: string[], isPrefetching: boolean) {
    if (isPrefetching) {
      sentenceIds.forEach((sentenceId) => prefetchingSentenceIdsRef.current.add(sentenceId));
    } else {
      sentenceIds.forEach((sentenceId) => prefetchingSentenceIdsRef.current.delete(sentenceId));
    }
    setPrefetchingSentenceIds(new Set(prefetchingSentenceIdsRef.current));
  }

  async function prefetchSentences(sentences: Sentence[]) {
    const sentenceIds = sentences
      .map((sentence) => sentence.id)
      .filter((sentenceId) => {
        const audio = audioAssetsBySentenceId[sentenceId];
        return !(
          (audio?.status === "ready" && audio.audio_url) ||
          prefetchingSentenceIdsRef.current.has(sentenceId)
        );
      });
    if (sentenceIds.length === 0) {
      return;
    }
    setPrefetching(sentenceIds, true);
    try {
      const response = await prefetchSentenceAudio(sentenceIds);
      rememberAudioAssets(response.assets);
      response.assets.forEach((audio) => {
        if (audio.audio_url) {
          audioCacheRef.current.set(audio.sentence_id, Promise.resolve(audio));
        }
      });
    } catch {
      // Automatic prefetch should never interrupt reading.
    } finally {
      setPrefetching(sentenceIds, false);
    }
  }

  useEffect(() => {
    const pendingIds = Object.values(audioAssetsBySentenceId)
      .filter((audio) => audio.status === "pending" || audio.status === "generating")
      .map((audio) => audio.sentence_id);
    if (pendingIds.length === 0) {
      return;
    }
    const intervalId = window.setInterval(async () => {
      try {
        rememberAudioAssets(await fetchSentenceAudioStatuses(pendingIds));
      } catch {
        // Polling is best effort; direct playback still has a blocking fallback.
      }
    }, AUDIO_STATUS_POLL_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [audioAssetsBySentenceId]);

  function getSentenceAudio(sentence: Sentence) {
    const cached = audioCacheRef.current.get(sentence.id);
    if (cached) {
      return cached;
    }
    const request = generateSentenceAudio(sentence.id)
      .then(waitForSentenceAudio)
      .catch((error) => {
        audioCacheRef.current.delete(sentence.id);
        throw error;
      });
    audioCacheRef.current.set(sentence.id, request);
    return request;
  }

  async function waitForSentenceAudio(initial: AudioAsset) {
    let audio = initial;
    for (let attempt = 0; attempt < AUDIO_READY_MAX_POLLS; attempt += 1) {
      rememberAudioAssets([audio]);
      if (audio.status === "ready" && audio.audio_url) return audio;
      if (audio.status === "failed") throw new Error("音频生成失败，请稍后重试");
      await new Promise((resolve) => window.setTimeout(resolve, AUDIO_READY_POLL_INTERVAL_MS));
      const [nextAudio] = await fetchSentenceAudioStatuses([audio.sentence_id]);
      if (nextAudio) audio = nextAudio;
    }
    throw new Error("音频生成超时，请确认后台 worker 正在运行");
  }

  function prefetchSentencesAfter(sentence: Sentence) {
    const index = flatSentences.findIndex((item) => item.id === sentence.id);
    if (index !== -1) {
      void prefetchSentences(
        flatSentences.slice(index + 1, index + 1 + PLAYBACK_PREFETCH_SENTENCE_COUNT)
      );
    }
  }

  async function prefetchChapter(chapter: Chapter) {
    setActivePrefetchChapterId(chapter.id);
    try {
      const response = await prefetchChapterAudio(chapter.id);
      rememberAudioAssets(response.assets);
      response.assets.forEach((audio) => {
        if (audio.audio_url) audioCacheRef.current.set(audio.sentence_id, Promise.resolve(audio));
      });
    } catch (error) {
      setError(error instanceof Error ? error.message : "章节音频预生成失败");
    } finally {
      setActivePrefetchChapterId(null);
    }
  }

  function getSentenceAudioState(sentenceId: string) {
    const audio = audioAssetsBySentenceId[sentenceId];
    if (audio?.status === "ready" && audio.audio_url) return "ready";
    if (audio?.status === "failed") return "failed";
    if (
      prefetchingSentenceIds.has(sentenceId) ||
      audio?.status === "pending" ||
      audio?.status === "generating"
    ) {
      return "generating";
    }
    return "idle";
  }

  function getChapterAudioProgress(chapter: Chapter) {
    const sentences = chapter.paragraphs.flatMap((paragraph) => paragraph.sentences);
    return {
      failed: sentences.filter((sentence) => getSentenceAudioState(sentence.id) === "failed")
        .length,
      generating: sentences.filter(
        (sentence) => getSentenceAudioState(sentence.id) === "generating"
      ).length,
      ready: sentences.filter((sentence) => getSentenceAudioState(sentence.id) === "ready")
        .length,
      total: sentences.length
    };
  }

  async function seekAudio(audio: HTMLAudioElement, audioPositionMs: number) {
    if (audioPositionMs <= 0) return;
    if (audio.readyState < HTMLMediaElement.HAVE_METADATA) {
      await new Promise<void>((resolve) => {
        const cleanup = () => {
          audio.removeEventListener("loadedmetadata", cleanup);
          audio.removeEventListener("error", cleanup);
          resolve();
        };
        audio.addEventListener("loadedmetadata", cleanup, { once: true });
        audio.addEventListener("error", cleanup, { once: true });
      });
    }
    try {
      audio.currentTime = audioPositionMs / 1000;
    } catch {
      // Playback can still start from the beginning if seeking is unavailable.
    }
  }

  async function playFrom(sentence: Sentence) {
    setCurrentSentenceId(sentence.id);
    const resumePositionMs = progress.getResumePositionMs(sentence.id);
    progress.save(sentence.id, resumePositionMs);
    setIsGeneratingAudio(true);
    setError(null);
    try {
      const audio = await getSentenceAudio(sentence);
      if (!audio.audio_url) throw new Error("音频还未生成完成");
      if (audioRef.current) {
        audioRef.current.src = audio.audio_url;
        audioRef.current.load();
        await seekAudio(audioRef.current, resumePositionMs);
        await audioRef.current.play();
      }
      progress.clearRestoredPosition();
      setIsPlaying(true);
      prefetchSentencesAfter(sentence);
    } catch (error) {
      setIsPlaying(false);
      setError(error instanceof Error ? error.message : "播放失败");
    } finally {
      setIsGeneratingAudio(false);
    }
  }

  async function moveSentence(offset: number) {
    if (flatSentences.length === 0) return;
    const foundIndex = flatSentences.findIndex((sentence) => sentence.id === currentSentenceId);
    const currentIndex = foundIndex === -1 ? (offset > 0 ? -1 : 0) : foundIndex;
    const nextIndex = Math.min(flatSentences.length - 1, Math.max(0, currentIndex + offset));
    const sentence = flatSentences[nextIndex];
    if (isPlaying) {
      await playFrom(sentence);
    } else {
      setCurrentSentenceId(sentence.id);
      progress.clearRestoredPosition();
      progress.save(sentence.id, 0);
    }
  }

  async function playNextSentence() {
    const currentIndex = flatSentences.findIndex((sentence) => sentence.id === currentSentenceId);
    if (currentIndex === -1 || currentIndex + 1 >= flatSentences.length) {
      setIsPlaying(false);
      return;
    }
    await playFrom(flatSentences[currentIndex + 1]);
  }

  async function togglePlayback() {
    if (isPlaying) {
      progress.save(currentSentenceId, progress.getAudioPositionMs());
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }
    const sentence = currentSentence ?? flatSentences[0];
    if (sentence) await playFrom(sentence);
  }

  return {
    activePrefetchChapterId,
    audioRef,
    chapters,
    clear,
    currentSentence,
    currentSentenceId,
    getChapterAudioProgress,
    getSentenceAudioState,
    isGeneratingAudio,
    isLoadingChapters,
    isPlaying,
    loadChapters,
    moveSentence,
    playFrom,
    playNextSentence,
    prefetchChapter,
    prefetchSentences,
    selectBook,
    selectedBookId,
    selectUploadedBook,
    setIsPlaying,
    togglePlayback
  };
}
