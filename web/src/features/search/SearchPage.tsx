import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, ShieldCheck, Sparkles, Filter } from 'lucide-react';
import { VideoCard, VideoData } from '../../entities/VideoCard';
import { apiFetch } from '../../shared/api';

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const filterType = searchParams.get('filter') || '';

  const [videos, setVideos] = useState<VideoData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!query.trim()) {
      setVideos([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    const filterParam = filterType ? `&filter_type=${filterType}` : '';
    apiFetch<VideoData[]>(`/search?q=${encodeURIComponent(query.trim())}${filterParam}`)
      .then((data) => setVideos(data || []))
      .catch((err) => {
        console.error('Search failed:', err);
        setVideos([]);
      })
      .finally(() => setLoading(false));
  }, [query, filterType]);

  const setFilter = (type: string) => {
    setSearchParams({ q: query, ...(type ? { filter: type } : {}) });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Search Header */}
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-indigo-500" />
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Search Results for <span className="text-indigo-600 dark:text-indigo-400">"{query}"</span>
            </h1>
          </div>

          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
            <span>Career Guardrails Enforced</span>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pt-2 pb-1">
          <button
            onClick={() => setFilter('')}
            className={`rounded-full px-3.5 py-1 text-xs font-semibold shrink-0 transition-colors ${
              !filterType
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
            }`}
          >
            All Results
          </button>
          <button
            onClick={() => setFilter('tutorials')}
            className={`rounded-full px-3.5 py-1 text-xs font-semibold shrink-0 transition-colors ${
              filterType === 'tutorials'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
            }`}
          >
            Tutorials
          </button>
          <button
            onClick={() => setFilter('courses')}
            className={`rounded-full px-3.5 py-1 text-xs font-semibold shrink-0 transition-colors ${
              filterType === 'courses'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
            }`}
          >
            Full Courses (&gt;30m)
          </button>
          <button
            onClick={() => setFilter('talks')}
            className={`rounded-full px-3.5 py-1 text-xs font-semibold shrink-0 transition-colors ${
              filterType === 'talks'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300'
            }`}
          >
            Tech Talks
          </button>
        </div>
      </div>

      {/* Videos Grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex flex-col gap-2">
              <div className="aspect-video w-full animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800" />
              <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
            </div>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 p-12 text-center dark:border-gray-800">
          <Sparkles className="h-10 w-10 text-indigo-500" />
          <h3 className="mt-3 text-base font-bold text-gray-900 dark:text-white">
            No career-focused videos found for "{query}"
          </h3>
          <p className="mt-1 max-w-md text-xs text-gray-500 leading-relaxed">
            MyTube blocks pure entertainment, comedy, pranks, memes, and clickbait to keep you focused.
            Try searching for engineering topics like "Distributed Systems", "TypeScript Design Patterns",
            "PostgreSQL Performance", or "System Architecture".
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {videos.map((v) => (
            <VideoCard key={v.youtube_id || v.id} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
