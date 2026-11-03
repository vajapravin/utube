import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Sparkles } from 'lucide-react';
import { apiFetch } from '../../shared/api';

interface Category {
  id: string;
  slug: string;
  name: string;
  icon: string;
}

export function OnboardingPicker() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch<Category[]>('/categories')
      .then((data) => {
        setCategories(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleCategory = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      if (selectedIds.length < 10) {
        setSelectedIds([...selectedIds, id]);
      }
    }
  };

  const handleContinue = async () => {
    if (selectedIds.length < 3) return;
    setSaving(true);
    try {
      await apiFetch('/me/interests', {
        method: 'PUT',
        body: JSON.stringify({ category_ids: selectedIds }),
      });
      navigate('/');
    } catch (err) {
      alert('Failed to save interests: ' + err);
      setSaving(false);
    }
  };

  const isValid = selectedIds.length >= 3 && selectedIds.length <= 10;

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-4 py-12">
      <div className="text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Step 1 of 1: Personalize</span>
        </div>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
          Choose your interests
        </h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Select between 3 and 10 categories to build your personalized video dashboard.
        </p>
      </div>

      <div className="mt-8 flex flex-wrap justify-center gap-2.5">
        {categories.map((cat) => {
          const selected = selectedIds.includes(cat.id);
          return (
            <button
              key={cat.id}
              onClick={() => toggleCategory(cat.id)}
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all ${
                selected
                  ? 'bg-indigo-600 text-white shadow-sm hover:bg-indigo-700'
                  : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              {selected && <Check className="h-4 w-4" />}
              <span>{cat.name}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-10 flex flex-col items-center gap-2">
        <button
          onClick={handleContinue}
          disabled={!isValid || saving}
          className={`flex items-center justify-center rounded-full px-8 py-3 text-sm font-semibold transition-all ${
            isValid && !saving
              ? 'bg-indigo-600 text-white shadow-md hover:bg-indigo-700'
              : 'cursor-not-allowed bg-gray-200 text-gray-400 dark:bg-gray-800 dark:text-gray-600'
          }`}
        >
          {saving ? 'Saving...' : `Continue (${selectedIds.length}/3 chosen)`}
        </button>
        <span className="text-xs text-gray-400">
          {selectedIds.length < 3
            ? `Pick at least ${3 - selectedIds.length} more`
            : `${selectedIds.length} selected`}
        </span>
      </div>
    </div>
  );
}
