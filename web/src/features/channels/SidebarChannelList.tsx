import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FolderPlus, Sparkles, Tv, RefreshCw } from 'lucide-react';
import { apiFetch } from '../../shared/api';

interface ChannelItem {
  id: string;
  name: string;
  handle: string;
  status: string;
  video_count?: number;
}

interface SidebarChannelListProps {
  collapsed?: boolean;
  onSelect?: () => void;
}

export function SidebarChannelList({ collapsed = false, onSelect }: SidebarChannelListProps) {
  const location = useLocation();

  const { data: channels = [], isLoading } = useQuery<ChannelItem[]>({
    queryKey: ['channels', 'mine'],
    queryFn: () => apiFetch<ChannelItem[]>('/channels'),
    staleTime: 10_000,
    refetchInterval: (query) => {
      // Auto-poll every 4s if any channel is still curating
      const data = query.state.data;
      if (data && data.some((c) => c.status === 'curating')) {
        return 4000;
      }
      return false;
    },
  });

  return (
    <div className="flex flex-col gap-1">
      {/* Section Header */}
      {!collapsed ? (
        <div className="flex items-center justify-between px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          <span>My Channels</span>
          <Link
            to="/channels/new"
            onClick={onSelect}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-indigo-600 dark:hover:bg-gray-800 dark:hover:text-indigo-400"
            title="Create new AI channel"
          >
            <FolderPlus className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <div className="my-1 flex justify-center">
          <Link
            to="/channels/new"
            onClick={onSelect}
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 hover:text-indigo-600 dark:hover:bg-gray-800 dark:hover:text-indigo-400"
            title="Create new AI channel"
          >
            <FolderPlus className="h-4 w-4" />
          </Link>
        </div>
      )}

      {/* Loading state */}
      {isLoading && channels.length === 0 && (
        <div className="px-3 py-2 text-xs text-gray-400">Loading...</div>
      )}

      {/* Empty state */}
      {!isLoading && channels.length === 0 && !collapsed && (
        <div className="px-3 py-2 text-xs text-gray-400">
          No channels yet.{' '}
          <Link to="/channels/new" onClick={onSelect} className="text-indigo-600 hover:underline dark:text-indigo-400">
            Create one
          </Link>
        </div>
      )}

      {/* Channel list */}
      {channels.map((channel) => {
        const isActive = location.pathname.startsWith(`/ch/${channel.handle}`);
        const initial = (channel.name || 'C').charAt(0).toUpperCase();

        return (
          <Link
            key={channel.id}
            to={`/ch/${channel.handle}/videos`}
            onClick={onSelect}
            title={`${channel.name} (${channel.handle})`}
            className={`group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-300'
                : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
            }`}
          >
            {/* Channel Avatar */}
            <div className="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 text-xs font-bold text-white shadow-sm">
              <span>{initial}</span>
              {channel.status === 'curating' && (
                <span className="absolute -bottom-0.5 -right-0.5 flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500" />
                </span>
              )}
            </div>

            {/* Channel Name & Handle */}
            {!collapsed && (
              <div className="flex min-w-0 flex-1 items-center justify-between">
                <span className="truncate">{channel.name}</span>
                {channel.status === 'curating' && (
                  <RefreshCw className="h-3 w-3 shrink-0 animate-spin text-amber-500" />
                )}
              </div>
            )}
          </Link>
        );
      })}
    </div>
  );
}
