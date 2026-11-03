import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, ListMusic, Play } from 'lucide-react';
import { apiFetch } from '../../shared/api';

interface Playlist {
  id: string;
  title: string;
  description?: string;
  item_count: number;
  system_kind?: string;
}

export function PlaylistsPage() {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Playlist[]>('/playlists')
      .then((data) => {
        setPlaylists(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

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

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Your Library</h1>
          <p className="text-sm text-gray-500">Manage playlists and saved videos.</p>
        </div>

        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1.5 rounded-full bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          <span>New Playlist</span>
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="flex gap-2 max-w-md">
          <input
            type="text"
            required
            placeholder="Playlist title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="flex-1 rounded-xl border border-gray-300 bg-white p-2 text-sm dark:border-gray-700 dark:bg-gray-900"
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
        <div className="text-gray-500">Loading playlists...</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {playlists.map((pl) => (
            <Link
              key={pl.id}
              to={`/playlist/${pl.id}`}
              className="flex flex-col gap-2 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm hover:border-indigo-500 dark:border-gray-800 dark:bg-gray-900"
            >
              <div className="flex h-32 w-full items-center justify-center rounded-xl bg-gray-100 text-gray-400 dark:bg-gray-800">
                <ListMusic className="h-10 w-10 text-indigo-500" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{pl.title}</h3>
              <p className="text-xs text-gray-500">
                {pl.system_kind ? 'System playlist' : `${pl.item_count || 0} videos`}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
