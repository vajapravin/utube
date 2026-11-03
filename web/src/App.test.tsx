import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { SignInPage } from './features/auth/SignInPage';

describe('SignInPage', () => {
  it('renders Google sign in button and app branding', () => {
    render(<SignInPage />);
    expect(screen.getByText('Welcome to mytube')).toBeDefined();
    expect(screen.getByText('Continue with Google')).toBeDefined();
  });
});
