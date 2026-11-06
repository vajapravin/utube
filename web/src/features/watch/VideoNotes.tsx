import React, { useEffect, useState } from 'react';
import { BookOpen, Check, Save } from 'lucide-react';
import { apiFetch } from '../../shared/api';

export function VideoNotes({
  youtubeId,
  onSeek,
}: {
  youtubeId: string;
  onSeek?: (seconds: number) => void;
}) {
  const [content, setContent] = useState('');
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch<{ content: string; updated_at?: string }>(`/videos/${youtubeId}/notes`)
      .then((data) => {
        setContent(data.content || '');
        setSavedAt(data.updated_at || null);
      })
      .catch((err) => console.error('Failed to load notes:', err))
      .finally(() => setLoading(false));
  }, [youtubeId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await apiFetch<{ content: string; updated_at: string }>(
        `/videos/${youtubeId}/notes`,
        {
          method: 'PUT',
          body: JSON.stringify({ content }),
        }
      );
      setSavedAt(res.updated_at);
    } catch (err) {
      alert('Failed to save notes: ' + err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-center justify-between border-b border-gray-100 pb-2.5 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-indigo-500" />
          <h3 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-wider">
            Study Notes & Key Takeaways
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {savedAt && (
            <span className="text-[11px] text-gray-400">
              Saved {new Date(savedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? (
              <span>Saving...</span>
            ) : (
              <>
                <Save className="h-3 w-3" />
                <span>Save</span>
              </>
            )}
          </button>
        </div>
      </div>

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Write personal insights, code snippets, or timestamp notes (e.g. 04:30 explains indexing algorithm)..."
        rows={4}
        className="w-full resize-y rounded-xl border border-gray-200 bg-gray-50/70 p-3 text-xs text-gray-900 focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-gray-800 dark:bg-gray-800/50 dark:text-gray-100 dark:focus:bg-gray-900"
      />
    </div>
  );
}
