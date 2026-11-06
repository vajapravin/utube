import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Sparkles, Play } from 'lucide-react';
import { apiFetch } from '../../shared/api';

export function CreateChannelPage() {
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState('private');
  const [previewPlan, setPreviewPlan] = useState<any>(null);
  const [previewing, setPreviewing] = useState(false);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handlePreview = async () => {
    if (prompt.length < 20) return;
    setPreviewing(true);
    try {
      const plan = await apiFetch('/channels/preview-plan', {
        method: 'POST',
        body: JSON.stringify({ prompt }),
      });
      setPreviewPlan(plan);
    } catch (err) {
      alert('Plan preview failed: ' + err);
    } finally {
      setPreviewing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.length < 20 || name.length < 3) return;
    setCreating(true);
    try {
      const ch: any = await apiFetch('/channels', {
        method: 'POST',
        body: JSON.stringify({
          name,
          prompt,
          description,
          visibility,
        }),
      });
      await queryClient.invalidateQueries({ queryKey: ['channels', 'mine'] });
      navigate(`/ch/${ch.handle}/videos`);
    } catch (err) {
      alert('Failed to create channel: ' + err);
      setCreating(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl py-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Create AI-Curated Channel</h1>
      <p className="mt-1 text-sm text-gray-500">
        Define a channel using a natural language prompt. Our AI will curate matching videos and shorts.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-5">
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Channel Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. ESP32 Robotics & IoT Tutorials"
            className="mt-1 w-full rounded-xl border border-gray-300 bg-white p-2.5 text-sm dark:border-gray-700 dark:bg-gray-900"
          />
          {name.length > 0 && name.length < 3 && (
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
              Channel name must be at least 3 characters.
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">
            Description <span className="font-normal text-gray-400">(Optional)</span>
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief summary of what this channel focuses on"
            className="mt-1 w-full rounded-xl border border-gray-300 bg-white p-2.5 text-sm dark:border-gray-700 dark:bg-gray-900"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Curation Prompt</label>
          <textarea
            required
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Beginner-friendly ESP32 and IoT tutorials, English, under 25 minutes, no clickbait, clear circuit schematics"
            className="mt-1 w-full rounded-xl border border-gray-300 bg-white p-2.5 text-sm dark:border-gray-700 dark:bg-gray-900"
          />
          <span className="text-xs text-gray-400">{prompt.length} / 2000 chars (min 20)</span>
          {prompt.length > 0 && prompt.length < 20 && (
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
              Prompt must be at least 20 characters (currently {prompt.length}).
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">Visibility</label>
          <select
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
            className="mt-1 w-full rounded-xl border border-gray-300 bg-white p-2.5 text-sm dark:border-gray-700 dark:bg-gray-900"
          >
            <option value="private">Private (Only you can see this channel)</option>
            <option value="unlisted">Unlisted (Anyone with the link can view)</option>
            <option value="public">Public (Listed on Explore page)</option>
          </select>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={handlePreview}
            disabled={prompt.length < 20 || previewing}
            className="flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
          >
            <Sparkles className="h-4 w-4" />
            <span>{previewing ? 'Analyzing...' : 'Preview Plan'}</span>
          </button>

          <button
            type="submit"
            disabled={prompt.length < 20 || name.length < 3 || creating}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <span>{creating ? 'Creating...' : 'Create & Curate Channel'}</span>
          </button>
        </div>
      </form>

      {/* Plan Preview Box (FR-31) */}
      {previewPlan && (
        <div className="mt-8 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 dark:border-indigo-900/50 dark:bg-indigo-950/20">
          <h3 className="font-semibold text-indigo-900 dark:text-indigo-200">Generated Search Plan Preview</h3>
          <div className="mt-3 flex flex-col gap-2 text-xs">
            <div>
              <span className="font-bold">Queries: </span>
              <span>{previewPlan.queries?.join(', ')}</span>
            </div>
            {previewPlan.exclude_terms?.length > 0 && (
              <div>
                <span className="font-bold">Excluding: </span>
                <span>{previewPlan.exclude_terms?.join(', ')}</span>
              </div>
            )}
            <div>
              <span className="font-bold">Max Duration: </span>
              <span>{previewPlan.max_duration_s ? `${previewPlan.max_duration_s}s` : 'Any'}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
