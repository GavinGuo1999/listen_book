import { BookOpen, Loader2 } from "lucide-react";
import type { RefObject } from "react";

import { PlayerBar } from "../components/PlayerBar";
import type { BookSummary, Chapter, Sentence } from "../types";

type AudioProgress = { failed: number; generating: number; ready: number; total: number };

type ReaderPageProps = {
  activePrefetchChapterId: string | null;
  audioRef: RefObject<HTMLAudioElement>;
  chapters: Chapter[];
  currentSentence: Sentence | null;
  currentSentenceId: string | null;
  error: string | null;
  isGeneratingAudio: boolean;
  isLoadingChapters: boolean;
  isPlaying: boolean;
  selectedBook: BookSummary | null;
  getChapterAudioProgress: (chapter: Chapter) => AudioProgress;
  getSentenceAudioState: (sentenceId: string) => string;
  onAudioEnded: () => void;
  onAudioPause: () => void;
  onAudioPlay: () => void;
  onMoveSentence: (offset: number) => void;
  onPlayFrom: (sentence: Sentence) => void;
  onPrefetchChapter: (chapter: Chapter) => void;
  onPrefetchSentences: (sentences: Sentence[]) => void;
  onRefresh: () => void;
  onTogglePlayback: () => void;
};

export function ReaderPage(props: ReaderPageProps) {
  const {
    activePrefetchChapterId,
    audioRef,
    chapters,
    currentSentence,
    currentSentenceId,
    error,
    isGeneratingAudio,
    isLoadingChapters,
    isPlaying,
    selectedBook,
    getChapterAudioProgress,
    getSentenceAudioState,
    onAudioEnded,
    onAudioPause,
    onAudioPlay,
    onMoveSentence,
    onPlayFrom,
    onPrefetchChapter,
    onPrefetchSentences,
    onRefresh,
    onTogglePlayback
  } = props;

  const playerProps = {
    currentSentence,
    isGeneratingAudio,
    isPlaying,
    onMoveSentence,
    onTogglePlayback
  };

  return (
    <section className="reader-panel" data-testid="reader-panel">
      <header className="reader-header">
        <div><p className="eyebrow">阅读器</p><h2>{selectedBook?.title ?? "选择或上传一本书"}</h2></div>
        <button className="ghost-button" onClick={onRefresh} type="button">刷新</button>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      <PlayerBar {...playerProps} />
      <div className="reader-content" data-testid="reader-content">
        {isLoadingChapters ? (
          <div className="empty-state large"><Loader2 className="spin" size={24} /><span>加载正文</span></div>
        ) : chapters.length === 0 ? (
          <div className="empty-state large"><BookOpen size={28} /><span>{selectedBook ? "书籍还未解析完成" : "书库为空"}</span></div>
        ) : (
          chapters.map((chapter) => {
            const progress = getChapterAudioProgress(chapter);
            const isPrefetching = activePrefetchChapterId === chapter.id;
            return (
              <article className="chapter" key={chapter.id}>
                <div className="chapter-header">
                  <h3>{chapter.title}</h3>
                  <button className="chapter-prefetch-button" disabled={isPrefetching || progress.total === 0} onClick={() => onPrefetchChapter(chapter)} type="button">
                    {isPrefetching ? <Loader2 className="spin" size={14} /> : null}
                    <span>预生成本章 {progress.ready}/{progress.total}</span>
                  </button>
                </div>
                {chapter.paragraphs.map((paragraph) => (
                  <p key={paragraph.id}>
                    {paragraph.sentences.map((sentence) => {
                      const audioState = getSentenceAudioState(sentence.id);
                      return (
                        <button
                          className={sentence.id === currentSentenceId ? "sentence active" : "sentence"}
                          data-audio-state={audioState}
                          data-testid="sentence-button"
                          key={sentence.id}
                          onClick={() => onPlayFrom(sentence)}
                          onFocus={() => onPrefetchSentences([sentence])}
                          onMouseEnter={() => onPrefetchSentences([sentence])}
                          type="button"
                        >
                          {sentence.text}
                          <span aria-hidden="true" className={`sentence-audio-status ${audioState}`} />
                        </button>
                      );
                    })}
                  </p>
                ))}
              </article>
            );
          })
        )}
      </div>
      <PlayerBar {...playerProps} />
      <audio
        data-testid="sentence-audio"
        onEnded={onAudioEnded}
        onPause={onAudioPause}
        onPlay={onAudioPlay}
        preload="auto"
        ref={audioRef}
      />
    </section>
  );
}
