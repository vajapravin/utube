import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { VideoCard, VideoData } from '../../entities/VideoCard';
import { apiFetch } from '../../shared/api';

interface Category {
  id: string;
  slug: string;
  name: string;
}

interface Shelf {
  category: Category;
  videos: VideoData[];
}

interface FeedData {
  for_you: VideoData[];
  continue_watching: VideoData[];
  shorts: VideoData[];
  shelves: Shelf[];
}

export function HomePage() {
  const [data, setData] = useState<FeedData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<FeedData>('/feed/home')
      .then((feed) => {
        setData(feed);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="aspect-video w-full animate-pulse rounded-xl bg-gray-200 dark:bg-gray-800" />
            <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <p className="text-gray-500">Failed to load feed. Refresh to try again.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Continue Watching (FR-53) */}
      {data.continue_watching.length > 0 && (
        <section>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Continue Watching</h2>
          <div className="mt-3 flex gap-4 overflow-x-auto pb-2 scrollbar-none">
            {data.continue_watching.map((video) => (
              <div key={video.id} className="w-64 shrink-0">
                <VideoCard video={video} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* For You Grid (FR-21) */}
      {data.for_you.length > 0 && (
        <section>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">For You</h2>
          <div className="mt-3 grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {data.for_you.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        </section>
      )}

      {/* Shorts Shelf (FR-23) */}
      {data.shorts.length > 0 && (
        <section>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Shorts</h2>
            <Link to="/shorts" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              See all
            </Link>
          </div>
          <div className="mt-3 flex gap-4 overflow-x-auto pb-2 scrollbar-none">
            {data.shorts.map((video) => (
              <div key={video.id} className="w-40 shrink-0">
                <VideoCard video={video} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Category Shelves (FR-20) */}
      {data.shelves.map((shelf) => (
        <section key={shelf.category.id}>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">{shelf.category.name}</h2>
            <Link
              to={`/c/${shelf.category.slug}`}
              className="text-xs font-semibold text-indigo-600 hover:underline dark:text-indigo-400"
            >
              See all
            </Link>
          </div>
          <div className="mt-3 flex gap-4 overflow-x-auto pb-2 scrollbar-none">
            {shelf.videos.map((video) => (
              <div key={video.id} className="w-64 shrink-0">
                <VideoCard video={video} />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
