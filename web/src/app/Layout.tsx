import React, { useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import {
  Home,
  Compass,
  PlaySquare,
  Clock,
  ThumbsUp,
  FolderPlus,
  Settings,
  Search,
  Sun,
  Moon,
  Tv,
  LogOut,
  Menu,
  X,
  Layers,
} from 'lucide-react';
import { useTheme } from '../shared/theme';
import { apiFetch } from '../shared/api';
import { SidebarChannelList } from '../features/channels/SidebarChannelList';

export function Layout() {
  const { theme, setTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' });
    } catch {
      // Proceed
    }
    window.location.href = '/login';
  };

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-white dark:bg-gray-950">
      {/* Top Bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 px-4 dark:border-gray-800">
        <div className="flex items-center gap-4">
          {/* Desktop sidebar toggle button */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 sm:block dark:text-gray-400 dark:hover:bg-gray-800"
            title="Toggle Sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
          {/* Mobile drawer toggle button */}
          <button
            onClick={() => setMobileDrawerOpen(true)}
            className="rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 sm:hidden dark:text-gray-400 dark:hover:bg-gray-800"
            title="Open Menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-indigo-600 dark:text-indigo-400">
            <Tv className="h-6 w-6" />
            <span>mytube</span>
          </Link>
        </div>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex w-full max-w-md items-center">
          <div className="relative w-full">
            <input
              type="text"
              placeholder="Search catalog..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-full border border-gray-300 bg-gray-50 py-1.5 pl-4 pr-10 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white"
            />
            <button
              type="submit"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-900 dark:hover:text-white"
            >
              <Search className="h-4 w-4" />
            </button>
          </div>
        </form>

        {/* User Actions */}
        <div className="flex items-center gap-2">
          <Link
            to="/channels/new"
            className="hidden items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-600 hover:bg-indigo-100 sm:flex dark:bg-indigo-950/60 dark:text-indigo-300"
          >
            <FolderPlus className="h-4 w-4" />
            <span>New Channel</span>
          </Link>

          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="rounded-full p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            title="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <button
            onClick={handleLogout}
            className="rounded-full p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            title="Sign Out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Main Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Nav */}
        <aside
          className={`hidden border-r border-gray-200 transition-all duration-200 sm:flex sm:flex-col dark:border-gray-800 ${
            collapsed ? 'w-16' : 'w-56'
          } p-3 gap-1`}
        >
          <Link
            to="/"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <Home className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Home</span>}
          </Link>

          <Link
            to="/shorts"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <PlaySquare className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Shorts</span>}
          </Link>

          <Link
            to="/explore"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <Compass className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Explore</span>}
          </Link>

          <hr className="my-2 border-gray-200 dark:border-gray-800" />

          <Link
            to="/library"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <Clock className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Library</span>}
          </Link>

          <Link
            to="/me/likes"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <ThumbsUp className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Liked Videos</span>}
          </Link>

          <hr className="my-2 border-gray-200 dark:border-gray-800" />

          {/* User's Created Channels */}
          <div className="flex-1 overflow-y-auto">
            <SidebarChannelList collapsed={collapsed} />
          </div>

          <hr className="my-2 border-gray-200 dark:border-gray-800" />

          <Link
            to="/settings"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            <Settings className="h-5 w-5 shrink-0" />
            {!collapsed && <span>Settings</span>}
          </Link>
        </aside>

        {/* Content Outlet */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>

      {/* Mobile Slide-Over Drawer */}
      {mobileDrawerOpen && (
        <div className="fixed inset-0 z-50 flex sm:hidden">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileDrawerOpen(false)}
          />
          <div className="relative z-10 flex h-full w-4/5 max-w-xs flex-col justify-between bg-white p-4 shadow-2xl dark:bg-gray-900">
            <div className="flex flex-col gap-3 overflow-y-auto">
              <div className="flex items-center justify-between border-b border-gray-200 pb-3 dark:border-gray-800">
                <Link
                  to="/"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center gap-2 font-bold text-lg text-indigo-600 dark:text-indigo-400"
                >
                  <Tv className="h-6 w-6" />
                  <span>mytube</span>
                </Link>
                <button
                  onClick={() => setMobileDrawerOpen(false)}
                  className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="flex flex-col gap-1 text-sm font-medium">
                <Link
                  to="/"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  <Home className="h-5 w-5" />
                  <span>Home</span>
                </Link>
                <Link
                  to="/shorts"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  <PlaySquare className="h-5 w-5" />
                  <span>Shorts</span>
                </Link>
                <Link
                  to="/explore"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  <Compass className="h-5 w-5" />
                  <span>Explore</span>
                </Link>
                <Link
                  to="/library"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  <Clock className="h-5 w-5" />
                  <span>Library</span>
                </Link>
                <Link
                  to="/me/likes"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  <ThumbsUp className="h-5 w-5" />
                  <span>Liked Videos</span>
                </Link>
              </div>

              <hr className="my-2 border-gray-200 dark:border-gray-800" />

              {/* Channels in Mobile Drawer */}
              <div className="overflow-y-auto">
                <SidebarChannelList collapsed={false} onSelect={() => setMobileDrawerOpen(false)} />
              </div>
            </div>

            <div className="border-t border-gray-200 pt-3 dark:border-gray-800">
              <Link
                to="/settings"
                onClick={() => setMobileDrawerOpen(false)}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                <Settings className="h-5 w-5" />
                <span>Settings</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Bottom Tab Bar */}
      <nav className="flex h-14 items-center justify-around border-t border-gray-200 bg-white sm:hidden dark:border-gray-800 dark:bg-gray-950">
        <Link to="/" className="flex flex-col items-center text-xs text-gray-700 dark:text-gray-300">
          <Home className="h-5 w-5" />
          <span>Home</span>
        </Link>
        <button
          onClick={() => setMobileDrawerOpen(true)}
          className="flex flex-col items-center text-xs text-gray-700 dark:text-gray-300"
        >
          <Layers className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          <span>Channels</span>
        </button>
        <Link to="/channels/new" className="flex flex-col items-center text-xs text-gray-700 dark:text-gray-300">
          <FolderPlus className="h-5 w-5" />
          <span>New</span>
        </Link>
        <Link to="/library" className="flex flex-col items-center text-xs text-gray-700 dark:text-gray-300">
          <Clock className="h-5 w-5" />
          <span>Library</span>
        </Link>
        <Link to="/me/likes" className="flex flex-col items-center text-xs text-gray-700 dark:text-gray-300">
          <ThumbsUp className="h-5 w-5" />
          <span>Liked</span>
        </Link>
      </nav>
    </div>
  );
}
