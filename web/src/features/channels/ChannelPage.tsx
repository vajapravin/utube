import React, { useEffect, useState } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { RefreshCw, PlaySquare, Video as VideoIcon, ThumbsUp } from 'lucide-react';
import { VideoCard, VideoData } from '../../entities/VideoCard';
import { apiFetch } from '../../shared/api';

export function ChannelPage() {
  const { handle } = useParams<{ handle: string }>();
  const location = useLocation();
  const [channel, setChannel] = useState<any>(null);
  const [videos, setVideos] = useState<VideoData[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Active tab derived from URL
  const activeTab = location.pathname.endsWith('/shorts')
    ? 'shorts'
    : location.pathname.endsWith('/liked')
    ? 'liked'
    : 'videos';

  useEffect(() => {
    if (!handle) return;
    setLoading(true);

    apiFetch<any>(`/channels/by-handle/${handle}`)
      .then((ch) => {
        setChannel(ch);
        // Fetch videos for active tab
        const endpoint =
          activeTab === 'liked'
            ? `/channels/${ch.id}/liked`
            : `/channels/${ch.id}/videos${activeTab === 'shorts' ? '?kind=short' : '?kind=video'}`;

        return apiFetch<any>(endpoint);
      })
      .then((res) => {
        setVideos(res.items || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [handle, activeTab]);

  // Poll channel curation status if curating
  useEffect(() => {
    if (!channel || channel.status !== 'curating') return;

    const interval = setInterval(async () => {
      try {
        const st: any = await apiFetch(`/channels/${channel.id}/status`);
        if (st.status === 'ready') {
          setChannel((prev: any) => ({ ...prev, status: 'ready' }));
          const endpoint =
            activeTab === 'liked'
              ? `/channels/${channel.id}/liked`
              : `/channels/${channel.id}/videos${activeTab === 'shorts' ? '?kind=short' : '?kind=video'}`;
          const res: any = await apiFetch(endpoint);
          setVideos(res.items || []);
        }
      } catch (err) {
        console.error('Status poll error:', err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [channel?.id, channel?.status, activeTab]);

  const handleRefresh = async () => {
    if (!channel) return;
    setRefreshing(true);
    try {
      await apiFetch(`/channels/${channel.id}/refresh`, { method: 'POST' });
      setChannel((prev: any) => ({ ...prev, status: 'curating' }));
    } catch (err) {
      alert('Refresh failed: ' + err);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading channel...</div>;
  }

  if (!channel) {
    return <div className="p-8 text-center text-gray-500">Channel not found.</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Channel Header (FR-40) */}
      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
        <div className="h-32 w-full bg-gradient-to-r from-indigo-500 to-purple-600" />
        <div className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{channel.name}</h1>
              <p className="text-sm font-medium text-gray-500">{channel.handle}</p>
              {channel.description && (
                <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{channel.description}</p>
              )}
            </div>

            {channel.is_owner && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="flex items-center gap-1.5 rounded-full border border-gray-300 bg-white px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>
            )}
          </div>

          {/* Owner Prompt Panel */}
          {channel.prompt && (
            <div className="mt-4 rounded-xl bg-gray-50 p-3 text-xs text-gray-600 dark:bg-gray-800/50 dark:text-gray-400">
              <span className="font-semibold text-gray-900 dark:text-white">Curator Prompt: </span>
              <span>{channel.prompt}</span>
            </div>
          )}

          {/* Navigation Tabs (FR-40) */}
          <div className="mt-6 flex gap-6 border-b border-gray-200 text-sm font-semibold dark:border-gray-800">
            <Link
              to={`/ch/${handle}/videos`}
              className={`flex items-center gap-2 pb-3 border-b-2 transition-all ${
                activeTab === 'videos'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            >
              <VideoIcon className="h-4 w-4" />
              <span>Videos</span>
            </Link>

            <Link
              to={`/ch/${handle}/shorts`}
              className={`flex items-center gap-2 pb-3 border-b-2 transition-all ${
                activeTab === 'shorts'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            >
              <PlaySquare className="h-4 w-4" />
              <span>Shorts</span>
            </Link>

            <Link
              to={`/ch/${handle}/liked`}
              className={`flex items-center gap-2 pb-3 border-b-2 transition-all ${
                activeTab === 'liked'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
              }`}
            >
              <ThumbsUp className="h-4 w-4" />
              <span>Liked</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Curation in progress banner */}
      {channel.status === 'curating' && (
        <div className="flex items-center gap-3 rounded-2xl border border-indigo-200 bg-indigo-50/80 p-4 dark:border-indigo-800 dark:bg-indigo-950/30">
          <RefreshCw className="h-5 w-5 animate-spin text-indigo-600 dark:text-indigo-400" />
          <div>
            <p className="text-sm font-semibold text-indigo-900 dark:text-indigo-200">
              AI curation in progress...
            </p>
            <p className="text-xs text-indigo-700 dark:text-indigo-400">
              Discovering and scoring matching videos for your channel. This page will update automatically.
            </p>
          </div>
        </div>
      )}

      {/* Video Grid for Active Tab */}
      {videos.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 p-12 text-center text-sm text-gray-500 dark:border-gray-800">
          {channel.status === 'curating'
            ? 'Curating initial videos for your channel. Please wait a few moments...'
            : activeTab === 'liked'
            ? 'Videos you like in this channel will show up here.'
            : 'No videos found in this tab. Try refreshing curation.'}
        </div>
      ) : (
        <div
          className={`grid gap-5 ${
            activeTab === 'shorts'
              ? 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6'
              : 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4'
          }`}
        >
          {videos.map((v) => (
            <VideoCard key={v.id} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
