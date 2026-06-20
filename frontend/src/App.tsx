import {
  BookOpen,
  Loader2,
  LogOut,
  Pause,
  Play,
  SkipBack,
  SkipForward,
  Trash2,
  Upload,
  UserRound
} from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  deleteBook as deleteBookRequest,
  fetchCurrentUser,
  fetchBookProgress,
  fetchSentenceAudioStatuses,
  fetchBooks,
  fetchChapters,
  generateSentenceAudio,
  getStoredAuthToken,
  loginUser,
  prefetchSentenceAudio,
  registerUser,
  saveBookProgress,
  setStoredAuthToken,
  uploadBook
} from "./api";
import type { AudioAsset, BookSummary, Chapter, Sentence, User } from "./types";

const PROCESSING_STATUSES = new Set(["uploaded", "parsing"]);
const INITIAL_PREFETCH_SENTENCE_COUNT = 5;
const PLAYBACK_PREFETCH_SENTENCE_COUNT = 8;
const PREFETCH_BATCH_SIZE = 20;
const AUDIO_STATUS_POLL_INTERVAL_MS = 2500;
const PROGRESS_SAVE_INTERVAL_MS = 5000;

type RestoredPlaybackPosition = {
  sentenceId: string;
  audioPositionMs: number;
};

type AuthMode = "login" | "register";

export function App() {
  const [books, setBooks] = useState<BookSummary[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedBookId, setSelectedBookId] = useState<string | null>(null);
  const [currentSentenceId, setCurrentSentenceId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [isLoadingBooks, setIsLoadingBooks] = useState(true);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);
  const [activePrefetchChapterId, setActivePrefetchChapterId] = useState<string | null>(null);
  const [deletingBookId, setDeletingBookId] = useState<string | null>(null);
  const [bookPendingDelete, setBookPendingDelete] = useState<BookSummary | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authDisplayName, setAuthDisplayName] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [audioAssetsBySentenceId, setAudioAssetsBySentenceId] = useState<Record<string, AudioAsset>>(
    {}
  );
  const [prefetchingSentenceIds, setPrefetchingSentenceIds] = useState<Set<string>>(
    () => new Set()
  );
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioCacheRef = useRef<Map<string, Promise<AudioAsset>>>(new Map());
  const audioPreloadRef = useRef<Map<string, HTMLAudioElement>>(new Map());
  const prefetchingSentenceIdsRef = useRef<Set<string>>(new Set());
  const restoredPlaybackPositionRef = useRef<RestoredPlaybackPosition | null>(null);

  useEffect(() => {
    loadCurrentUser();
    refreshBooks();
  }, []);

  async function loadCurrentUser() {
    try {
      const user = await fetchCurrentUser();
      setCurrentUser(user);
    } catch {
      setStoredAuthToken(null);
      setCurrentUser(null);
    }
  }

  async function refreshBooks(showLoading = true) {
    if (showLoading) {
      setIsLoadingBooks(true);
    }
    setError(null);
    try {
      const nextBooks = await fetchBooks();
      setBooks(nextBooks);
      return nextBooks;
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载书库失败");
      return [];
    } finally {
      if (showLoading) {
        setIsLoadingBooks(false);
      }
    }
  }

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError(null);
    setIsAuthSubmitting(true);
    try {
      const response =
        authMode === "login"
          ? await loginUser(authUsername, authPassword)
          : await registerUser(authUsername, authPassword, authDisplayName);
      setStoredAuthToken(response.access_token);
      setCurrentUser(response.user);
      setAuthPassword("");
      setAuthDisplayName("");
      clearCurrentBookState();
      await refreshBooks();
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "账号操作失败");
    } finally {
      setIsAuthSubmitting(false);
    }
  }

  async function logout() {
    setStoredAuthToken(null);
    setAuthError(null);
    clearCurrentBookState();
    await loadCurrentUser();
    await refreshBooks();
  }

  async function loadChapters(bookId: string) {
    setIsLoadingChapters(true);
    setError(null);
    try {
      const nextChapters = await fetchChapters(bookId);
      setChapters(nextChapters);
      const allSentences = nextChapters.flatMap((chapter) =>
        chapter.paragraphs.flatMap((p) => p.sentences)
      );

      try {
        const progress = await fetchBookProgress(bookId);
        const savedSentence = allSentences.find(
          (sentence) => sentence.id === progress?.sentence_id
        );
        if (savedSentence) {
          setCurrentSentenceId(savedSentence.id);
          restoredPlaybackPositionRef.current = {
            sentenceId: savedSentence.id,
            audioPositionMs: progress?.audio_position_ms ?? 0
          };
        } else {
          restoredPlaybackPositionRef.current = null;
        }
      } catch {
        // Progress restore is best effort; loading the book should still succeed.
        restoredPlaybackPositionRef.current = null;
      }

      const initialSentences = nextChapters
        .flatMap((chapter) => chapter.paragraphs.flatMap((p) => p.sentences))
        .slice(0, INITIAL_PREFETCH_SENTENCE_COUNT);
      prefetchSentences(initialSentences);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载正文失败");
      setChapters([]);
    } finally {
      setIsLoadingChapters(false);
    }
  }

  function getCurrentAudioPositionMs() {
    const audio = audioRef.current;
    if (!audio || !Number.isFinite(audio.currentTime)) {
      return 0;
    }
    return Math.max(0, Math.round(audio.currentTime * 1000));
  }

  function saveCurrentProgress(sentenceId: string | null, audioPositionMs = 0) {
    if (!selectedBookId) {
      return;
    }
    saveBookProgress(selectedBookId, sentenceId, audioPositionMs).catch(() => {
      // Progress saving should not interrupt reading or playback.
    });
  }

  function clearCurrentBookState() {
    audioRef.current?.pause();
    if (audioRef.current) {
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
    setSelectedBookId(null);
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
    restoredPlaybackPositionRef.current = null;
  }

  async function selectBook(book: BookSummary) {
    audioRef.current?.pause();
    setSelectedBookId(book.id);
    setCurrentSentenceId(null);
    setIsPlaying(false);
    setChapters([]);
    setAudioAssetsBySentenceId({});
    setPrefetchingSentenceIds(new Set());
    setActivePrefetchChapterId(null);
    audioCacheRef.current.clear();
    audioPreloadRef.current.clear();
    prefetchingSentenceIdsRef.current.clear();
    restoredPlaybackPositionRef.current = null;
    if (book.status === "ready") {
      await loadChapters(book.id);
    }
  }

  async function confirmDeleteBook() {
    if (!bookPendingDelete) {
      return;
    }

    const book = bookPendingDelete;
    setDeletingBookId(book.id);
    setError(null);
    try {
      await deleteBookRequest(book.id);
      setBooks((current) => current.filter((item) => item.id !== book.id));
      if (selectedBookId === book.id) {
        clearCurrentBookState();
      }
      setBookPendingDelete(null);
      await refreshBooks(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeletingBookId(null);
    }
  }

  async function handleUpload(file: File | undefined) {
    if (!file) {
      return;
    }

    setError(null);
    try {
      const book = await uploadBook(file);
      setBooks((current) => [book, ...current]);
      setSelectedBookId(book.id);
      setCurrentSentenceId(null);
      setIsPlaying(false);
      setChapters([]);
      setAudioAssetsBySentenceId({});
      setPrefetchingSentenceIds(new Set());
      setActivePrefetchChapterId(null);
      audioCacheRef.current.clear();
      audioPreloadRef.current.clear();
      prefetchingSentenceIdsRef.current.clear();
      restoredPlaybackPositionRef.current = null;
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    }
  }

  const selectedBook = useMemo(
    () => books.find((book) => book.id === selectedBookId) ?? null,
    [books, selectedBookId]
  );

  useEffect(() => {
    if (!selectedBook || !PROCESSING_STATUSES.has(selectedBook.status)) {
      return;
    }

    const intervalId = window.setInterval(async () => {
      const nextBooks = await refreshBooks(false);
      const updatedBook = nextBooks.find((book) => book.id === selectedBook.id);
      if (updatedBook?.status === "ready") {
        await loadChapters(updatedBook.id);
      }
      if (updatedBook?.status === "failed") {
        setError("书籍解析失败，请检查文件格式或稍后重试");
      }
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [selectedBook]);

  const flatSentences = useMemo(
    () => chapters.flatMap((chapter) => chapter.paragraphs.flatMap((p) => p.sentences)),
    [chapters]
  );

  const currentSentence = flatSentences.find((sentence) => sentence.id === currentSentenceId) ?? null;

  useEffect(() => {
    if (!isPlaying || !currentSentenceId || !selectedBookId) {
      return;
    }

    const intervalId = window.setInterval(() => {
      saveCurrentProgress(currentSentenceId, getCurrentAudioPositionMs());
    }, PROGRESS_SAVE_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [currentSentenceId, isPlaying, selectedBookId]);

  useEffect(() => {
    const pendingSentenceIds = Object.values(audioAssetsBySentenceId)
      .filter((audio) => audio.status === "pending" || audio.status === "generating")
      .map((audio) => audio.sentence_id);

    if (pendingSentenceIds.length === 0) {
      return;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const assets = await fetchSentenceAudioStatuses(pendingSentenceIds);
        rememberAudioAssets(assets);
      } catch {
        // Status polling is best effort; playback still has the blocking generate fallback.
      }
    }, AUDIO_STATUS_POLL_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [audioAssetsBySentenceId]);

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
    if (sentenceIds.length === 0) {
      return;
    }

    if (isPrefetching) {
      sentenceIds.forEach((sentenceId) => prefetchingSentenceIdsRef.current.add(sentenceId));
    } else {
      sentenceIds.forEach((sentenceId) => prefetchingSentenceIdsRef.current.delete(sentenceId));
    }
    setPrefetchingSentenceIds(new Set(prefetchingSentenceIdsRef.current));
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

  function getSentenceAudio(sentence: Sentence) {
    const cached = audioCacheRef.current.get(sentence.id);
    if (cached) {
      return cached;
    }

    const request = generateSentenceAudio(sentence.id)
      .then((audio) => {
        rememberAudioAssets([audio]);
        return audio;
      })
      .catch((err) => {
        audioCacheRef.current.delete(sentence.id);
        throw err;
      });

    audioCacheRef.current.set(sentence.id, request);
    return request;
  }

  async function prefetchSentences(sentences: Sentence[]) {
    const sentenceIds = sentences
      .map((sentence) => sentence.id)
      .filter((sentenceId) => {
        const audio = audioAssetsBySentenceId[sentenceId];
        if (audio?.status === "ready" && audio.audio_url) {
          return false;
        }
        if (prefetchingSentenceIdsRef.current.has(sentenceId)) {
          return false;
        }
        return true;
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
      // Hover/automatic prefetch should never interrupt reading.
    } finally {
      setPrefetching(sentenceIds, false);
    }
  }

  function prefetchSentencesAfter(sentence: Sentence) {
    const currentIndex = flatSentences.findIndex((item) => item.id === sentence.id);
    if (currentIndex === -1) {
      return;
    }

    prefetchSentences(
      flatSentences.slice(
        currentIndex + 1,
        currentIndex + 1 + PLAYBACK_PREFETCH_SENTENCE_COUNT
      )
    );
  }

  async function prefetchChapter(chapter: Chapter) {
    const sentences = chapter.paragraphs.flatMap((paragraph) => paragraph.sentences);
    if (sentences.length === 0) {
      return;
    }

    setActivePrefetchChapterId(chapter.id);
    try {
      for (let index = 0; index < sentences.length; index += PREFETCH_BATCH_SIZE) {
        await prefetchSentences(sentences.slice(index, index + PREFETCH_BATCH_SIZE));
      }
    } finally {
      setActivePrefetchChapterId(null);
    }
  }

  function getSentenceAudioState(sentenceId: string) {
    const audio = audioAssetsBySentenceId[sentenceId];
    if (audio?.status === "ready" && audio.audio_url) {
      return "ready";
    }
    if (audio?.status === "failed") {
      return "failed";
    }
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
    const ready = sentences.filter(
      (sentence) => getSentenceAudioState(sentence.id) === "ready"
    ).length;
    const generating = sentences.filter(
      (sentence) => getSentenceAudioState(sentence.id) === "generating"
    ).length;
    const failed = sentences.filter(
      (sentence) => getSentenceAudioState(sentence.id) === "failed"
    ).length;
    return { failed, generating, ready, total: sentences.length };
  }

  async function moveSentence(offset: number) {
    if (flatSentences.length === 0) {
      return;
    }
    const foundIndex = flatSentences.findIndex((sentence) => sentence.id === currentSentenceId);
    const currentIndex = foundIndex === -1 ? (offset > 0 ? -1 : 0) : foundIndex;
    const nextIndex = Math.min(flatSentences.length - 1, Math.max(0, currentIndex + offset));
    const nextSentence = flatSentences[nextIndex];
    if (isPlaying) {
      await playFrom(nextSentence);
    } else {
      setCurrentSentenceId(nextSentence.id);
      restoredPlaybackPositionRef.current = null;
      saveCurrentProgress(nextSentence.id, 0);
    }
  }

  async function playNextSentence() {
    const currentIndex = flatSentences.findIndex((sentence) => sentence.id === currentSentenceId);
    const nextIndex = currentIndex + 1;
    if (currentIndex === -1 || nextIndex >= flatSentences.length) {
      setIsPlaying(false);
      return;
    }
    await playFrom(flatSentences[nextIndex]);
  }

  function getResumePositionMs(sentenceId: string) {
    const restoredPosition = restoredPlaybackPositionRef.current;
    if (restoredPosition?.sentenceId !== sentenceId) {
      return 0;
    }
    return restoredPosition.audioPositionMs;
  }

  async function seekAudio(audio: HTMLAudioElement, audioPositionMs: number) {
    if (audioPositionMs <= 0) {
      return;
    }

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
      // If the browser cannot seek yet, playback should still start from the beginning.
    }
  }

  async function playFrom(sentence: Sentence) {
    setCurrentSentenceId(sentence.id);
    const resumePositionMs = getResumePositionMs(sentence.id);
    saveCurrentProgress(sentence.id, resumePositionMs);
    setIsGeneratingAudio(true);
    setError(null);
    try {
      const audio = await getSentenceAudio(sentence);
      if (!audio.audio_url) {
        throw new Error("音频还未生成完成");
      }
      if (audioRef.current) {
        audioRef.current.src = audio.audio_url;
        audioRef.current.load();
        await seekAudio(audioRef.current, resumePositionMs);
        await audioRef.current.play();
      }
      restoredPlaybackPositionRef.current = null;
      setIsPlaying(true);
      prefetchSentencesAfter(sentence);
    } catch (err) {
      setIsPlaying(false);
      setError(err instanceof Error ? err.message : "播放失败");
    } finally {
      setIsGeneratingAudio(false);
    }
  }

  async function togglePlayback() {
    if (isPlaying) {
      saveCurrentProgress(currentSentenceId, getCurrentAudioPositionMs());
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    const sentence = currentSentence ?? flatSentences[0];
    if (sentence) {
      await playFrom(sentence);
    }
  }

  return (
    <main className="app-shell" data-testid="app-shell">
      <aside className="library-panel" data-testid="library-panel">
        <div className="brand-row">
          <BookOpen size={22} />
          <h1>Listen Book</h1>
        </div>

        <section className="account-card" data-testid="account-card">
          <div className="account-current">
            <UserRound size={18} />
            <div>
              <span>{currentUser?.display_name ?? "Local Reader"}</span>
              <small>
                {getStoredAuthToken() ? `@${currentUser?.username}` : "本地模式 · 未登录"}
              </small>
            </div>
            {getStoredAuthToken() ? (
              <button aria-label="退出登录" onClick={logout} title="退出登录" type="button">
                <LogOut size={15} />
              </button>
            ) : null}
          </div>

          {!getStoredAuthToken() ? (
            <form className="auth-form" onSubmit={handleAuthSubmit}>
              <div className="auth-tabs">
                <button
                  className={authMode === "login" ? "active" : ""}
                  onClick={() => setAuthMode("login")}
                  type="button"
                >
                  登录
                </button>
                <button
                  className={authMode === "register" ? "active" : ""}
                  onClick={() => setAuthMode("register")}
                  type="button"
                >
                  注册
                </button>
              </div>
              <input
                autoComplete="username"
                onChange={(event) => setAuthUsername(event.target.value)}
                placeholder="用户名"
                required
                type="text"
                value={authUsername}
              />
              {authMode === "register" ? (
                <input
                  onChange={(event) => setAuthDisplayName(event.target.value)}
                  placeholder="显示名（可选）"
                  type="text"
                  value={authDisplayName}
                />
              ) : null}
              <input
                autoComplete={authMode === "login" ? "current-password" : "new-password"}
                minLength={6}
                onChange={(event) => setAuthPassword(event.target.value)}
                placeholder="密码"
                required
                type="password"
                value={authPassword}
              />
              {authError ? <p className="auth-error">{authError}</p> : null}
              <button disabled={isAuthSubmitting} type="submit">
                {isAuthSubmitting ? <Loader2 className="spin" size={14} /> : null}
                {authMode === "login" ? "登录账号" : "创建账号"}
              </button>
            </form>
          ) : null}
        </section>

        <label className="upload-button" data-testid="upload-book">
          <Upload size={18} />
          <span>上传书籍</span>
          <input
            accept=".txt,.epub,.pdf"
            type="file"
            onChange={(event) => handleUpload(event.target.files?.[0])}
          />
        </label>

        <div className="book-list" data-testid="book-list">
          {isLoadingBooks ? (
            <div className="empty-state">
              <Loader2 className="spin" size={18} />
              <span>加载中</span>
            </div>
          ) : (
            books.map((book) => (
              <div
                className={book.id === selectedBookId ? "book-row active" : "book-row"}
                data-testid="book-row"
                key={book.id}
              >
                <button
                  className="book-select-button"
                  onClick={() => selectBook(book)}
                  type="button"
                >
                  <span className="book-title">{book.title}</span>
                  <span className={`status ${book.status}`}>{book.status}</span>
                </button>
                <button
                  aria-label={`删除 ${book.title}`}
                  className="book-delete-button"
                  disabled={deletingBookId === book.id}
                  onClick={() => setBookPendingDelete(book)}
                  title="删除书籍"
                  type="button"
                >
                  {deletingBookId === book.id ? (
                    <Loader2 className="spin" size={15} />
                  ) : (
                    <Trash2 size={15} />
                  )}
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      <section className="reader-panel" data-testid="reader-panel">
        <header className="reader-header">
          <div>
            <p className="eyebrow">阅读器</p>
            <h2>{selectedBook?.title ?? "选择或上传一本书"}</h2>
          </div>
          <button className="ghost-button" onClick={() => refreshBooks()} type="button">
            刷新
          </button>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        <footer className="player-bar">
          <button
            aria-label="上一句"
            data-testid="previous-sentence"
            onClick={() => moveSentence(-1)}
            type="button"
          >
            <SkipBack size={20} />
          </button>
          <button
            aria-label={isPlaying ? "暂停" : "播放"}
            className="primary-control"
            data-testid="play-toggle"
            disabled={isGeneratingAudio}
            onClick={togglePlayback}
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
            onClick={() => moveSentence(1)}
            type="button"
          >
            <SkipForward size={20} />
          </button>
          <div className="now-playing">
            <span>当前句</span>
            <strong>{currentSentence?.text ?? "未选择"}</strong>
          </div>
        </footer>

        <div className="reader-content" data-testid="reader-content">
          {isLoadingChapters ? (
            <div className="empty-state large">
              <Loader2 className="spin" size={24} />
              <span>加载正文</span>
            </div>
          ) : chapters.length === 0 ? (
            <div className="empty-state large">
              <BookOpen size={28} />
              <span>{selectedBook ? "书籍还未解析完成" : "书库为空"}</span>
            </div>
          ) : (
            chapters.map((chapter) => {
              const progress = getChapterAudioProgress(chapter);
              const isPrefetchingChapter = activePrefetchChapterId === chapter.id;
              return (
                <article className="chapter" key={chapter.id}>
                  <div className="chapter-header">
                    <h3>{chapter.title}</h3>
                    <button
                      className="chapter-prefetch-button"
                      disabled={isPrefetchingChapter || progress.total === 0}
                      onClick={() => prefetchChapter(chapter)}
                      type="button"
                    >
                      {isPrefetchingChapter ? <Loader2 className="spin" size={14} /> : null}
                      <span>
                        预生成本章 {progress.ready}/{progress.total}
                      </span>
                    </button>
                  </div>
                  {chapter.paragraphs.map((paragraph) => (
                    <p key={paragraph.id}>
                      {paragraph.sentences.map((sentence) => {
                        const audioState = getSentenceAudioState(sentence.id);
                        return (
                          <button
                            className={
                              sentence.id === currentSentenceId ? "sentence active" : "sentence"
                            }
                            data-audio-state={audioState}
                            data-testid="sentence-button"
                            key={sentence.id}
                            onFocus={() => prefetchSentences([sentence])}
                            onMouseEnter={() => prefetchSentences([sentence])}
                            onClick={() => playFrom(sentence)}
                            type="button"
                          >
                            {sentence.text}
                            <span
                              aria-hidden="true"
                              className={`sentence-audio-status ${audioState}`}
                            />
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

        <footer className="player-bar">
          <button
            aria-label="上一句"
            data-testid="previous-sentence"
            onClick={() => moveSentence(-1)}
            type="button"
          >
            <SkipBack size={20} />
          </button>
          <button
            aria-label={isPlaying ? "暂停" : "播放"}
            className="primary-control"
            data-testid="play-toggle"
            disabled={isGeneratingAudio}
            onClick={togglePlayback}
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
            onClick={() => moveSentence(1)}
            type="button"
          >
            <SkipForward size={20} />
          </button>
          <div className="now-playing">
            <span>当前句</span>
            <strong>{currentSentence?.text ?? "未选择"}</strong>
          </div>
        </footer>
        <audio
          data-testid="sentence-audio"
          onEnded={playNextSentence}
          onPause={() => setIsPlaying(false)}
          onPlay={() => setIsPlaying(true)}
          preload="auto"
          ref={audioRef}
        />
      </section>

      {bookPendingDelete ? (
        <div className="modal-backdrop" role="presentation">
          <section
            aria-labelledby="delete-book-title"
            aria-modal="true"
            className="confirm-dialog"
            role="dialog"
          >
            <div>
              <p className="eyebrow">删除书籍</p>
              <h2 id="delete-book-title">确定删除《{bookPendingDelete.title}》？</h2>
            </div>
            <p className="confirm-copy">
              删除后会清理这本书的正文、上传源文件、已生成音频和本地阅读状态。这个操作不能撤销。
            </p>
            <div className="confirm-actions">
              <button
                className="ghost-button"
                disabled={deletingBookId === bookPendingDelete.id}
                onClick={() => setBookPendingDelete(null)}
                type="button"
              >
                取消
              </button>
              <button
                className="danger-button"
                disabled={deletingBookId === bookPendingDelete.id}
                onClick={confirmDeleteBook}
                type="button"
              >
                {deletingBookId === bookPendingDelete.id ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <Trash2 size={16} />
                )}
                <span>确认删除</span>
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
