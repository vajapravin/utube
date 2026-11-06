import React, { useEffect, useState } from 'react';
import {
  Youtube,
  RefreshCw,
  Upload,
  Link as LinkIcon,
  CheckCircle2,
  AlertCircle,
  FolderSync,
  Heart,
  History,
} from 'lucide-react';
import { apiFetch } from '../../shared/api';

interface SyncStatus {
  connected: boolean;
  has_refresh_token: boolean;
}

export function YouTubeSyncSection({ onSyncCompleted }: { onSyncCompleted?: () => void }) {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [syncingLiked, setSyncingLiked] = useState(false);
  const [syncingPlaylists, setSyncingPlaylists] = useState(false);
  const [importingPl, setImportingPl] = useState(false);
  const [uploadingTakeout, setUploadingTakeout] = useState(false);
  const [playlistInput, setPlaylistInput] = useState('');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await apiFetch<SyncStatus>('/youtube/status');
      setStatus(res);
    } catch {
      setStatus({ connected: false, has_refresh_token: false });
    } finally {
      setLoadingStatus(false);
    }
  };

  const handleSyncLiked = async () => {
    setSyncingLiked(true);
    setMessage(null);
    try {
      const res = await apiFetch<{ synced_count: number; message: string }>('/youtube/sync/liked', {
        method: 'POST',
      });
      setMessage({ type: 'success', text: res.message || `Synced ${res.synced_count} liked videos.` });
      onSyncCompleted?.();
    } catch (err) {
      setMessage({ type: 'error', text: String(err) });
    } finally {
      setSyncingLiked(false);
    }
  };

  const handleSyncPlaylists = async () => {
    setSyncingPlaylists(true);
    setMessage(null);
    try {
      const res = await apiFetch<{ playlists_synced: number; total_videos_synced: number }>(
        '/youtube/sync/playlists',
        { method: 'POST' }
      );
      setMessage({
        type: 'success',
        text: `Successfully synced ${res.playlists_synced} playlists (${res.total_videos_synced} videos).`,
      });
      onSyncCompleted?.();
    } catch (err) {
      setMessage({ type: 'error', text: String(err) });
    } finally {
      setSyncingPlaylists(false);
    }
  };

  const handleImportPlaylistUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!playlistInput.trim()) return;
    setImportingPl(true);
    setMessage(null);
    try {
      const res = await apiFetch<{ title: string; items_count: number }>('/youtube/import-playlist', {
        method: 'POST',
        body: JSON.stringify({ url_or_id: playlistInput.trim() }),
      });
      setMessage({
        type: 'success',
        text: `Imported playlist "${res.title}" with ${res.items_count} videos!`,
      });
      setPlaylistInput('');
      onSyncCompleted?.();
    } catch (err) {
      setMessage({ type: 'error', text: String(err) });
    } finally {
      setImportingPl(false);
    }
  };

  const handleTakeoutUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingTakeout(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      // Get CSRF cookie value
      const csrfMatch = document.cookie.match(/mytube_csrf=([^;]+)/);
      const csrfToken = csrfMatch ? csrfMatch[1] : '';

      const resp = await fetch('/api/v1/youtube/sync/takeout-history', {
        method: 'POST',
        headers: {
          'x-csrf-token': csrfToken,
        },
        body: formData,
      });
      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Upload failed');
      }
      const data = await resp.json();
      setMessage({
        type: 'success',
        text: data.message || `Imported ${data.imported_count} history items!`,
      });
      onSyncCompleted?.();
    } catch (err) {
      setMessage({ type: 'error', text: String(err) });
    } finally {
      setUploadingTakeout(false);
      e.target.value = '';
    }
  };

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 pb-4 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-100 text-red-600 dark:bg-red-950/50 dark:text-red-400">
            <Youtube className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-gray-900 dark:text-white">YouTube Integration</h2>
            <p className="text-xs text-gray-500">
              Sync your YouTube liked videos, playlists, and watch history
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {loadingStatus ? (
            <span className="text-xs text-gray-400">Checking connection...</span>
          ) : status?.connected ? (
            <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>OAuth Connected</span>
            </div>
          ) : (
            <a
              href="/api/v1/auth/connect-youtube"
              className="flex items-center gap-1.5 rounded-full bg-red-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-red-700 shadow-sm"
            >
              <Youtube className="h-3.5 w-3.5" />
              <span>Connect YouTube Account</span>
            </a>
          )}
        </div>
      </div>

      {message && (
        <div
          className={`flex items-start gap-2 rounded-xl p-3 text-xs font-medium ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300'
              : 'bg-red-50 text-red-800 dark:bg-red-950/50 dark:text-red-300'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Grid of Sync Actions */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Sync Liked Videos */}
        <div className="flex flex-col justify-between rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-800/50">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
              <Heart className="h-4 w-4 text-red-500" />
              <span>Sync Liked Videos</span>
            </div>
            <p className="mt-1 text-xs text-gray-500 leading-relaxed">
              Fetches your liked videos directly from YouTube with anti-entertainment filtering.
            </p>
          </div>
          <button
            onClick={handleSyncLiked}
            disabled={syncingLiked || !status?.connected}
            className="mt-4 flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncingLiked ? 'animate-spin' : ''}`} />
            <span>{syncingLiked ? 'Syncing...' : 'Sync Liked Videos'}</span>
          </button>
        </div>

        {/* Sync User Playlists */}
        <div className="flex flex-col justify-between rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-800/50">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
              <FolderSync className="h-4 w-4 text-indigo-500" />
              <span>Sync Playlists</span>
            </div>
            <p className="mt-1 text-xs text-gray-500 leading-relaxed">
              Imports all your private and public YouTube playlists into your MyTube library.
            </p>
          </div>
          <button
            onClick={handleSyncPlaylists}
            disabled={syncingPlaylists || !status?.connected}
            className="mt-4 flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <FolderSync className={`h-3.5 w-3.5 ${syncingPlaylists ? 'animate-spin' : ''}`} />
            <span>{syncingPlaylists ? 'Syncing...' : 'Sync All Playlists'}</span>
          </button>
        </div>

        {/* Google Takeout History Importer */}
        <div className="flex flex-col justify-between rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-800/50">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
              <History className="h-4 w-4 text-emerald-500" />
              <span>Takeout Watch History</span>
            </div>
            <p className="mt-1 text-xs text-gray-500 leading-relaxed">
              Upload your Google Takeout <code className="text-[11px] bg-gray-200 dark:bg-gray-700 px-1 rounded">watch-history.json</code> file to restore full history.
            </p>
          </div>
          <label className="mt-4 flex cursor-pointer items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 shadow-sm">
            <Upload className="h-3.5 w-3.5" />
            <span>{uploadingTakeout ? 'Processing...' : 'Upload watch-history.json'}</span>
            <input
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={handleTakeoutUpload}
              disabled={uploadingTakeout}
            />
          </label>
        </div>
      </div>

      {/* Import Public Playlist by URL */}
      <form
        onSubmit={handleImportPlaylistUrl}
        className="flex flex-col gap-2 rounded-xl border border-gray-100 bg-gray-50 p-3.5 sm:flex-row sm:items-center dark:border-gray-800 dark:bg-gray-800/50"
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-gray-700 dark:text-gray-300 shrink-0">
          <LinkIcon className="h-4 w-4 text-indigo-500" />
          <span>Import Playlist by URL:</span>
        </div>
        <input
          type="text"
          placeholder="https://www.youtube.com/playlist?list=PL... or Playlist ID"
          value={playlistInput}
          onChange={(e) => setPlaylistInput(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white"
        />
        <button
          type="submit"
          disabled={importingPl || !playlistInput.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {importingPl ? 'Importing...' : 'Import'}
        </button>
      </form>
    </div>
  );
}
