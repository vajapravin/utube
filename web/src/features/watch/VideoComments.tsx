import React, { useEffect, useState } from 'react';
import { MessageSquare, ThumbsUp, User } from 'lucide-react';
import { apiFetch } from '../../shared/api';

interface Comment {
  id: string;
  author: string;
  author_avatar?: string;
  text: string;
  like_count: number;
  published_at?: string;
}

export function VideoComments({ youtubeId }: { youtubeId: string }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch<Comment[]>(`/videos/${youtubeId}/comments`)
      .then((data) => setComments(data || []))
      .catch((err) => console.error('Failed to load comments:', err))
      .finally(() => setLoading(false));
  }, [youtubeId]);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-center gap-2 border-b border-gray-100 pb-2.5 dark:border-gray-800">
        <MessageSquare className="h-4 w-4 text-indigo-500" />
        <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider">
          Community Discussions ({comments.length})
        </h3>
      </div>

      {loading ? (
        <div className="text-xs text-gray-500 py-4 text-center">Loading discussions...</div>
      ) : comments.length === 0 ? (
        <div className="text-xs text-gray-500 py-4 text-center">
          No comments retrieved for this video.
        </div>
      ) : (
        <div className="flex flex-col gap-3 max-h-96 overflow-y-auto pr-1">
          {comments.map((c) => (
            <div key={c.id} className="flex items-start gap-2.5 text-xs">
              {c.author_avatar ? (
                <img
                  src={c.author_avatar}
                  alt={c.author}
                  className="h-7 w-7 rounded-full object-cover shrink-0"
                />
              ) : (
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-800 shrink-0 text-gray-500">
                  <User className="h-4 w-4" />
                </div>
              )}
              <div className="flex flex-1 flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900 dark:text-gray-100">{c.author}</span>
                  {c.published_at && (
                    <span className="text-[10px] text-gray-400">
                      {new Date(c.published_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-gray-700 dark:text-gray-300 leading-relaxed break-words whitespace-pre-line">
                  {c.text}
                </p>
                {c.like_count > 0 && (
                  <div className="mt-1 flex items-center gap-1 text-[11px] text-gray-400">
                    <ThumbsUp className="h-3 w-3" />
                    <span>{c.like_count}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
