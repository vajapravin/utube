import React, { useEffect, useState } from 'react';
import { X, Plus, Check, ListMusic } from 'lucide-react';
import { apiFetch } from '../../shared/api';

interface Playlist {
  id: string;
  title: string;
  system_kind?: string;
}

export function SaveToPlaylistModal({
  youtubeId,
  onClose,
}: {
  youtubeId: string;
  onClose: () => void;
}) {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [savedPlaylistIds, setSavedPlaylistIds] = useState<Set<string>>(new Set());
  const [newTitle, setNewTitle] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [youtubeId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [allPls, savedIn] = await Promise.all([
        apiFetch<Playlist[]>('/playlists'),
        apiFetch<Playlist[]>(`/videos/${youtubeId}/saved-in`),
      ]);
      setPlaylists(allPls);
      setSavedPlaylistIds(new Set(savedIn.map((p) => p.id)));
    } catch (err) {
      console.error('Failed to load playlists:', err);
    } finally {
      setLoading(false);
    }
  };

  const togglePlaylist = async (playlistId: string) => {
    const isSaved = savedPlaylistIds.has(playlistId);
    const nextSaved = new Set(savedPlaylistIds);
    if (isSaved) {
      nextSaved.delete(playlistId);
    } else {
      nextSaved.add(playlistId);
    }
    setSavedPlaylistIds(nextSaved);

    try {
      if (!isSaved) {
        await apiFetch(`/playlists/${playlistId}/items`, {
          method: 'POST',
          body: JSON.stringify({ youtube_id: youtubeId }),
        });
      }
    } catch (err) {
      alert('Failed to update playlist: ' + err);
      setSavedPlaylistIds(savedPlaylistIds); // Rollback
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const created = await apiFetch<Playlist>('/playlists', {
        method: 'POST',
        body: JSON.stringify({ title: newTitle.trim(), visibility: 'private' }),
      });
      // Add video to new playlist
      await apiFetch(`/playlists/${created.id}/items`, {
        method: 'POST',
        body: JSON.stringify({ youtube_id: youtubeId }),
      });
      setPlaylists([created, ...playlists]);
      setSavedPlaylistIds(new Set([...savedPlaylistIds, created.id]));
      setNewTitle('');
      setShowCreate(false);
    } catch (err) {
      alert('Failed to create playlist: ' + err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-5 shadow-2xl dark:border-gray-800 dark:bg-gray-900">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3 dark:border-gray-800">
          <div className="flex items-center gap-2 text-sm font-bold text-gray-900 dark:text-white">
            <ListMusic className="h-4 w-4 text-indigo-500" />
            <span>Save video to...</span>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-3 max-h-60 overflow-y-auto flex flex-col gap-1">
          {loading ? (
            <div className="p-4 text-center text-xs text-gray-500">Loading playlists...</div>
          ) : playlists.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">No playlists found.</div>
          ) : (
            playlists.map((pl) => {
              const isChecked = savedPlaylistIds.has(pl.id);
              return (
                <button
                  key={pl.id}
                  onClick={() => togglePlaylist(pl.id)}
                  className="flex items-center justify-between rounded-xl px-3 py-2 text-left text-xs font-medium text-gray-800 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800/60"
                >
                  <span className="truncate">{pl.title}</span>
                  <div
                    className={`flex h-4 w-4 items-center justify-center rounded border ${
                      isChecked
                        ? 'border-indigo-600 bg-indigo-600 text-white'
                        : 'border-gray-300 dark:border-gray-600'
                    }`}
                  >
                    {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                  </div>
                </button>
              );
            })
          )}
        </div>

        <div className="mt-4 border-t border-gray-100 pt-3 dark:border-gray-800">
          {showCreate ? (
            <form onSubmit={handleCreate} className="flex gap-2">
              <input
                type="text"
                required
                placeholder="New playlist title"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-white"
              />
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
              >
                Create
              </button>
            </form>
          ) : (
            <button
              onClick={() => setShowCreate(true)}
              className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-gray-200 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              <Plus className="h-3.5 w-3.5 text-indigo-500" />
              <span>Create new playlist</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
