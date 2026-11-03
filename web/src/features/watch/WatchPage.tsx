import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ThumbsUp, Share2, Bookmark, Check } from 'lucide-react';
import { VideoCard, VideoData } from '../../entities/VideoCard';
import { apiFetch } from '../../shared/api';

export function WatchPage() {
  const { id } = useParams<{ id: string }>();
  const [video, setVideo] = useState<VideoData | null>(null);
  const [upNext, setUpNext] = useState<VideoData[]>([]);
  const [isLiked, setIsLiked] = useState(false);
  const [copied, setCopied] = useState(false);

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
  }, [id]);

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

  if (!id) return null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 lg:flex-row">
      {/* Primary Player & Details Area */}
      <div className="flex-1">
        {/* Responsive Player Embed (FR-50) */}
        <div className="aspect-video w-full overflow-hidden rounded-2xl bg-black shadow-lg">
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${id}?enablejsapi=1&rel=0`}
            title={video?.title || 'YouTube Player'}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="h-full w-full border-0"
          />
        </div>

        {/* Title & Channel Header */}
        <div className="mt-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            {video?.title || 'Loading video...'}
          </h1>

          <div className="mt-3 flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-4 dark:border-gray-800">
            <div>
              <span className="font-semibold text-gray-900 dark:text-white">
                {video?.source_channel_title || 'YouTube Creator'}
              </span>
              <p className="text-xs text-gray-500">Content from YouTube</p>
            </div>

            {/* Action Bar (FR-51) */}
            <div className="flex items-center gap-2">
              <button
                onClick={toggleLike}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                  isLiked
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                <ThumbsUp className="h-4 w-4" />
                <span>{isLiked ? 'Liked' : 'Like'}</span>
              </button>

              <button
                onClick={handleShare}
                className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300"
              >
                {copied ? <Check className="h-4 w-4 text-green-500" /> : <Share2 className="h-4 w-4" />}
                <span>{copied ? 'Link Copied' : 'Share'}</span>
              </button>

              <button
                onClick={() => alert('Save to playlist dialog')}
                className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300"
              >
                <Bookmark className="h-4 w-4" />
                <span>Save</span>
              </button>
            </div>
          </div>

          {/* Description */}
          {video?.description && (
            <div className="mt-4 rounded-xl bg-gray-100 p-4 text-sm text-gray-800 dark:bg-gray-900 dark:text-gray-300">
              <p className="whitespace-pre-line leading-relaxed">{video.description}</p>
            </div>
          )}
        </div>
      </div>

      {/* Up Next Sidebar (FR-52) */}
      <div className="w-full lg:w-80 shrink-0">
        <h2 className="mb-3 text-sm font-bold text-gray-900 dark:text-white">Up Next</h2>
        <div className="flex flex-col gap-3">
          {upNext.map((v) => (
            <VideoCard key={v.id} video={v} />
          ))}
        </div>
      </div>
    </div>
  );
}
