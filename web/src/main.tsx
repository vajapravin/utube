import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './app/Layout';
import { SignInPage } from './features/auth/SignInPage';
import { OnboardingPicker } from './features/onboarding/OnboardingPicker';
import { HomePage } from './features/feed/HomePage';
import { WatchPage } from './features/watch/WatchPage';
import { ChannelPage } from './features/channels/ChannelPage';
import { CreateChannelPage } from './features/channels/CreateChannelPage';
import { PlaylistsPage } from './features/playlists/PlaylistsPage';
import { ThemeProvider } from './shared/theme';
import './index.css';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<SignInPage />} />
            <Route path="/onboarding" element={<OnboardingPicker />} />
            <Route path="/" element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="watch/:id" element={<WatchPage />} />
              <Route path="shorts" element={<HomePage />} />
              <Route path="explore" element={<HomePage />} />
              <Route path="library" element={<PlaylistsPage />} />
              <Route path="channels/new" element={<CreateChannelPage />} />
              <Route path="ch/:handle/*" element={<ChannelPage />} />
              <Route
                path="*"
                element={
                  <div className="flex h-96 flex-col items-center justify-center text-center">
                    <h2 className="text-3xl font-bold">404</h2>
                    <p className="mt-2 text-sm text-gray-500">Page not found.</p>
                  </div>
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
