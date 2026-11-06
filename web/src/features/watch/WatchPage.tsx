import React, { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ThumbsUp,
  Share2,
  Bookmark,
  Check,
  FastForward,
  ListOrdered,
  BookOpen,
  MessageSquare,
  FileText,
  ShieldCheck,
} from 'lucide-react';
import { VideoCard, VideoData } from '../../entities/VideoCard';
import { apiFetch } from '../../shared/api';
import { VideoNotes } from './VideoNotes';
import { VideoComments } from './VideoComments';
import { SaveToPlaylistModal } from './SaveToPlaylistModal';

interface Chapter {
  seconds: number;
  timestamp: string;
  title: string;
}

function extractChapters(description?: string): Chapter[] {
  if (!description) return [];
  const lines = description.split('\n');
  const chapters: Chapter[] = [];
  const regex = /(?:(\d{1,2}):)?(\d{2}):(\d{2})\s+[-–:]?\s*(.+)/;
  for (const line of lines) {
    const match = line.match(regex);
    if (match) {
      const h = match[1] ? parseInt(match[1], 10) : 0;
      const m = parseInt(match[2], 10);
      const s = parseInt(match[3], 10);
      const sec = h * 3600 + m * 60 + s;
      const title = match[4].trim();
      const ts = match[1] ? `${match[1]}:${match[2]}:${match[3]}` : `${match[2]}:${match[3]}`;
      chapters.push({ seconds: sec, timestamp: ts, title });
    }
  }
  return chapters;
}

export function WatchPage() {
  const { id } = useParams<{ id: string }>();
  const [video, setVideo] = useState<VideoData | null>(null);
  const [upNext, setUpNext] = useState<VideoData[]>([]);
  const [isLiked, setIsLiked] = useState(false);
  const [copied, setCopied] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<'notes' | 'chapters' | 'comments' | 'desc'>('notes');
  const [showSaveModal, setShowSaveModal] = useState(false);

  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!id) return;

    // Fetch video detail
    apiFetch<VideoData>(`/videos/${id}`)
      .then((v) => {
        setVideo(v);
        setIsLiked(Boolean(v.is_liked));
      })
      .catch((err) => console.error(err));

    // Fetch up-next
    apiFetch<VideoData[]>(`/videos/${id}/up-next`)
      .then(setUpNext)
      .catch((err) => console.error(err));

    // Record initial watch progress
    apiFetch(`/videos/${id}/progress`, {
      method: 'PUT',
      body: JSON.stringify({ progress_s: 1 }),
    }).catch(() => {});
  }, [id]);

  const sendPlayerCommand = (func: string, args: any[] = []) => {
    iframeRef.current?.contentWindow?.postMessage(
      JSON.stringify({ event: 'command', func, args }),
      '*'
    );
  };

  const handleSetSpeed = (speed: number) => {
    setPlaybackSpeed(speed);
    sendPlayerCommand('setPlaybackRate', [speed]);
  };

  const handleSeek = (seconds: number) => {
    sendPlayerCommand('seekTo', [seconds, true]);
    sendPlayerCommand('playVideo');
  };

  const toggleLike = async () => {
    if (!id) return;
    const nextState = !isLiked;
    setIsLiked(nextState);
    try {
      await apiFetch(`/videos/${id}/like`, { method: nextState ? 'PUT' : 'DELETE' });
    } catch {
      setIsLiked(!nextState); // Rollback
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const chapters = extractChapters(video?.description);

  if (!id) return null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 lg:flex-row">
      {/* Primary Player & Details Area */}
      <div className="flex-1">
        {/* Responsive Player Embed with JS API Enabled */}
        <div className="relative aspect-video w-full overflow-hidden rounded-2xl bg-black shadow-lg">
          <iframe
            ref={iframeRef}
            src={`https://www.youtube-nocookie.com/embed/${id}?enablejsapi=1&rel=0&autoplay=1`}
            title={video?.title || 'YouTube Player'}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="h-full w-full border-0"
          />
        </div>

        {/* Speed Controls & Career Banner */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-gray-100 p-2 text-xs dark:bg-gray-900">
          <div className="flex items-center gap-1.5 text-gray-700 dark:text-gray-300">
            <FastForward className="h-3.5 w-3.5 text-indigo-500" />
            <span className="font-semibold">Speed:</span>
            {[1, 1.25, 1.5, 1.75, 2].map((s) => (
              <button
                key={s}
                onClick={() => handleSetSpeed(s)}
                className={`rounded-lg px-2 py-0.5 text-xs font-semibold transition-colors ${
                  playbackSpeed === s
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Anti-Doom Mode Active</span>
          </div>
        </div>

        {/* Title & Channel Header */}
        <div className="mt-3">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white leading-snug">
            {video?.title || 'Loading video...'}
          </h1>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-4 dark:border-gray-800">
            <div>
              <span className="font-semibold text-gray-900 dark:text-white">
                {video?.source_channel_title || 'YouTube Creator'}
              </span>
              <p className="text-xs text-gray-500">Content from YouTube</p>
            </div>

            {/* Action Bar */}
            <div className="flex items-center gap-2">
              <button
                onClick={toggleLike}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold transition-all ${
                  isLiked
                    ? 'bg-red-600 text-white shadow-sm'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                <ThumbsUp className="h-3.5 w-3.5" />
                <span>{isLiked ? 'Liked' : 'Like'}</span>
              </button>

              <button
                onClick={handleShare}
                className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Share2 className="h-3.5 w-3.5" />}
                <span>{copied ? 'Copied' : 'Share'}</span>
              </button>

              <button
                onClick={() => setShowSaveModal(true)}
                className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300"
              >
                <Bookmark className="h-3.5 w-3.5" />
                <span>Save</span>
              </button>
            </div>
          </div>
        </div>

        {/* Tabbed Learning Workspace */}
        <div className="mt-4 flex flex-col gap-3">
          <div className="flex items-center gap-2 border-b border-gray-200 pb-1.5 dark:border-gray-800 overflow-x-auto">
            <button
              onClick={() => setActiveTab('notes')}
              className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold shrink-0 transition-colors ${
                activeTab === 'notes'
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
              }`}
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Study Notes</span>
            </button>

            {chapters.length > 0 && (
              <button
                onClick={() => setActiveTab('chapters')}
                className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold shrink-0 transition-colors ${
                  activeTab === 'chapters'
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                }`}
              >
                <ListOrdered className="h-3.5 w-3.5" />
                <span>Chapters ({chapters.length})</span>
              </button>
            )}

            <button
              onClick={() => setActiveTab('comments')}
              className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold shrink-0 transition-colors ${
                activeTab === 'comments'
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Discussions</span>
            </button>

            <button
              onClick={() => setActiveTab('desc')}
              className={`flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold shrink-0 transition-colors ${
                activeTab === 'desc'
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Description</span>
            </button>
          </div>

          {/* Active Tab Content */}
          {activeTab === 'notes' && (
            <VideoNotes youtubeId={id} onSeek={handleSeek} />
          )}

          {activeTab === 'chapters' && chapters.length > 0 && (
            <div className="flex flex-col gap-2 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900 max-h-80 overflow-y-auto">
              <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-1">
                Jump to Chapter
              </h3>
              {chapters.map((ch, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSeek(ch.seconds)}
                  className="flex items-center justify-between rounded-xl px-3 py-2 text-left text-xs hover:bg-indigo-50 dark:hover:bg-indigo-950/30 transition-colors group"
                >
                  <span className="font-medium text-gray-800 group-hover:text-indigo-600 dark:text-gray-200 dark:group-hover:text-indigo-400">
                    {ch.title}
                  </span>
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-[11px] font-mono font-semibold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                    {ch.timestamp}
                  </span>
                </button>
              ))}
            </div>
          )}

          {activeTab === 'comments' && (
            <VideoComments youtubeId={id} />
          )}

          {activeTab === 'desc' && (
            <div className="rounded-2xl border border-gray-200 bg-white p-4 text-xs text-gray-800 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300">
              <p className="whitespace-pre-line leading-relaxed">
                {video?.description || 'No description provided.'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Up Next Recommendation Sidebar */}
      <div className="w-full lg:w-80 shrink-0">
        <h2 className="mb-3 text-sm font-bold text-gray-900 dark:text-white">Related Career Videos</h2>
        <div className="flex flex-col gap-3">
          {upNext.map((v) => (
            <VideoCard key={v.youtube_id || v.id} video={v} />
          ))}
        </div>
      </div>

      {/* Save to Playlist Modal */}
      {showSaveModal && (
        <SaveToPlaylistModal
          youtubeId={id}
          onClose={() => setShowSaveModal(false)}
        />
      )}
    </div>
  );
}
