import React from 'react';
import { Link } from 'react-router-dom';
import { MoreVertical, Bookmark, Share2, EyeOff } from 'lucide-react';

export interface VideoData {
  id: string;
  youtube_id: string;
  title: string;
  description?: string;
  source_channel_title?: string;
  duration_s: number;
  is_short: boolean;
  aspect: string;
  thumbnails: {
    high?: { url: string };
    medium?: { url: string };
    default?: { url: string };
  };
  published_at: string;
  view_count?: number;
  is_liked?: boolean;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function VideoCard({ video }: { video: VideoData }) {
  const thumbUrl =
    video.thumbnails?.high?.url ||
    video.thumbnails?.medium?.url ||
    video.thumbnails?.default?.url ||
    `https://i.ytimg.com/vi/${video.youtube_id}/hqdefault.jpg`;

  const isShort = video.is_short;

  return (
    <div className="group flex flex-col gap-2 rounded-xl bg-transparent transition-all hover:translate-y-[-2px]">
      <Link
        to={`/watch/${video.youtube_id}`}
        className={`relative overflow-hidden rounded-xl bg-gray-200 dark:bg-gray-800 ${
          isShort ? 'aspect-[9/16]' : 'aspect-video'
        }`}
      >
        <img
          src={thumbUrl}
          alt={video.title}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
        <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-xs font-semibold text-white">
          {formatDuration(video.duration_s)}
        </span>
      </Link>

      <div className="flex gap-2.5 px-0.5">
        <div className="flex flex-1 flex-col">
          <Link
            to={`/watch/${video.youtube_id}`}
            className="line-clamp-2 text-sm font-semibold leading-snug text-gray-900 group-hover:text-indigo-600 dark:text-gray-100 dark:group-hover:text-indigo-400"
          >
            {video.title}
          </Link>
          <span className="mt-1 text-xs text-gray-600 dark:text-gray-400">
            {video.source_channel_title || 'YouTube Channel'}
          </span>
          <span className="text-[11px] text-gray-500">Content from YouTube</span>
        </div>

        <button
          className="h-7 w-7 rounded-full p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-800"
          title="Video options"
          onClick={(e) => {
            e.preventDefault();
            // Pop menu
          }}
        >
          <MoreVertical className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
