import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Plus,
  ListMusic,
  Heart,
  History,
  Youtube,
  Trash2,
  Play,
  RotateCcw,
} from 'lucide-react';
import { apiFetch } from '../../shared/api';
import { VideoCard, VideoData } from '../../entities/VideoCard';
import { YouTubeSyncSection } from '../youtube/YouTubeSyncSection';

interface Playlist {
  id: string;
  title: string;
  description?: string;
  item_count: number;
  system_kind?: string;
}

export function PlaylistsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'playlists';

  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [likedVideos, setLikedVideos] = useState<VideoData[]>([]);
  const [historyVideos, setHistoryVideos] = useState<VideoData[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);

  const setTab = (tab: string) => {
    setSearchParams({ tab });
  };

  const loadData = async () => {
    setLoading(true);
    try {
      if (currentTab === 'playlists') {
        const data = await apiFetch<Playlist[]>('/playlists');
        setPlaylists(data);
      } else if (currentTab === 'likes') {
        const data = await apiFetch<{ items: VideoData[] }>('/me/likes?limit=50');
        setLikedVideos(data.items || []);
      } else if (currentTab === 'history') {
        const data = await apiFetch<VideoData[]>('/me/history?limit=50');
        setHistoryVideos(data);
      }
    } catch (err) {
      console.error('Error loading library tab data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentTab]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      const pl = await apiFetch<Playlist>('/playlists', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim(), visibility: 'private' }),
      });
      setPlaylists([pl, ...playlists]);
      setTitle('');
      setShowCreate(false);
    } catch (err) {
      alert('Failed to create playlist: ' + err);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear your entire watch history?')) return;
    try {
      await apiFetch('/me/history', { method: 'DELETE' });
      setHistoryVideos([]);
    } catch (err) {
      alert('Failed to clear history: ' + err);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Your Career Library</h1>
          <p className="text-sm text-gray-500">
            Playlists, liked learning videos, watch history, and YouTube synchronization.
          </p>
        </div>

        {currentTab === 'playlists' && (
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 rounded-full bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 shadow-sm"
          >
            <Plus className="h-4 w-4" />
            <span>New Playlist</span>
          </button>
        )}

        {currentTab === 'history' && historyVideos.length > 0 && (
          <button
            onClick={handleClearHistory}
            className="flex items-center gap-1.5 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Clear History</span>
          </button>
        )}
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-2 border-b border-gray-200 pb-2 dark:border-gray-800 overflow-x-auto">
        <button
          onClick={() => setTab('playlists')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-colors shrink-0 ${
            currentTab === 'playlists'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
          }`}
        >
          <ListMusic className="h-4 w-4" />
          <span>Playlists ({playlists.length})</span>
        </button>

        <button
          onClick={() => setTab('likes')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-colors shrink-0 ${
            currentTab === 'likes'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
          }`}
        >
          <Heart className="h-4 w-4 text-red-400" />
          <span>Liked Videos</span>
        </button>

        <button
          onClick={() => setTab('history')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-colors shrink-0 ${
            currentTab === 'history'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
          }`}
        >
          <History className="h-4 w-4 text-emerald-400" />
          <span>Watch History</span>
        </button>

        <button
          onClick={() => setTab('sync')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-colors shrink-0 ${
            currentTab === 'sync'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
          }`}
        >
          <Youtube className="h-4 w-4 text-red-500" />
          <span>YouTube Sync</span>
        </button>
      </div>

      {/* Tab: YouTube Sync */}
      {currentTab === 'sync' && (
        <YouTubeSyncSection onSyncCompleted={() => loadData()} />
      )}

      {/* Tab: Playlists */}
      {currentTab === 'playlists' && (
        <>
          {showCreate && (
            <form onSubmit={handleCreate} className="flex gap-2 max-w-md">
              <input
                type="text"
                required
                placeholder="Playlist title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="flex-1 rounded-xl border border-gray-300 bg-white p-2.5 text-xs text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white"
              />
              <button
                type="submit"
                className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
              >
                Create
              </button>
            </form>
          )}

          {loading ? (
            <div className="text-xs text-gray-500 py-8">Loading playlists...</div>
          ) : playlists.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 p-8 text-center dark:border-gray-800">
              <ListMusic className="h-10 w-10 text-gray-400" />
              <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
                No playlists yet
              </h3>
              <p className="mt-1 text-xs text-gray-500">
                Create a custom learning playlist or sync from YouTube.
              </p>
              <button
                onClick={() => setTab('sync')}
                className="mt-4 rounded-full bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
              >
                Sync from YouTube
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {playlists.map((pl) => (
                <Link
                  key={pl.id}
                  to={`/playlist/${pl.id}`}
                  className="group flex flex-col gap-2 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm hover:border-indigo-500 dark:border-gray-800 dark:bg-gray-900 transition-colors"
                >
                  <div className="flex h-32 w-full items-center justify-center rounded-xl bg-gray-100 text-gray-400 dark:bg-gray-800 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-950/20">
                    <ListMusic className="h-10 w-10 text-indigo-500 transition-transform group-hover:scale-110" />
                  </div>
                  <h3 className="font-semibold text-sm text-gray-900 dark:text-white line-clamp-1">
                    {pl.title}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {pl.system_kind ? 'System playlist' : `${pl.item_count || 0} videos`}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab: Liked Videos */}
      {currentTab === 'likes' && (
        <div>
          {loading ? (
            <div className="text-xs text-gray-500 py-8">Loading liked videos...</div>
          ) : likedVideos.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 p-8 text-center dark:border-gray-800">
              <Heart className="h-10 w-10 text-red-400" />
              <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
                No liked videos yet
              </h3>
              <p className="mt-1 text-xs text-gray-500">
                Like videos while watching or import your liked videos from YouTube.
              </p>
              <button
                onClick={() => setTab('sync')}
                className="mt-4 rounded-full bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700"
              >
                Sync YouTube Liked Videos
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {likedVideos.map((video) => (
                <VideoCard key={video.youtube_id || video.id} video={video} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Watch History */}
      {currentTab === 'history' && (
        <div>
          {loading ? (
            <div className="text-xs text-gray-500 py-8">Loading watch history...</div>
          ) : historyVideos.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 p-8 text-center dark:border-gray-800">
              <History className="h-10 w-10 text-emerald-500" />
              <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
                No watch history yet
              </h3>
              <p className="mt-1 text-xs text-gray-500">
                Videos you watch will appear here with saved progress, or you can import Google Takeout history.
              </p>
              <button
                onClick={() => setTab('sync')}
                className="mt-4 rounded-full bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
              >
                Import Google Takeout History
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {historyVideos.map((video) => (
                <VideoCard key={video.youtube_id || video.id} video={video} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
