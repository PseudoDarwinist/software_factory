/**
 * Design Tokens for Mission Control
 * 
 * This file provides TypeScript access to our design system tokens.
 * All values are synchronized with the CSS variables in App.css.
 * 
 * Why this file exists:
 * - Provides TypeScript access to design tokens
 * - Enables programmatic color/spacing calculations
 * - Maintains consistency with CSS variables
 * 
 * For AI agents: Use these tokens for consistent styling in components.
 */

export const tokens = {
  colors: {
    // Base colors
    black: '#000000',
    white: '#ffffff',
    transparent: 'transparent',

    // Glass morphism colors
    glass: {
      primary: 'rgba(150, 179, 150, 0.15)',
      secondary: 'rgba(150, 179, 150, 0.08)',
      accent: 'rgba(150, 179, 150, 0.25)',
      neutral: 'rgba(255, 255, 255, 0.05)',
      dark: 'rgba(0, 0, 0, 0.2)',
    },

    // Surface colors
    surface: {
      primary: '#0a0a0a',
      secondary: '#1a1a1a',
      tertiary: '#2a2a2a',
      quaternary: '#3a3a3a',
      glass: 'rgba(255, 255, 255, 0.02)',
      glassHover: 'rgba(255, 255, 255, 0.05)',
      glassActive: 'rgba(255, 255, 255, 0.08)',
    },

    // Text colors
    text: {
      primary: '#ffffff',
      secondary: 'rgba(255, 255, 255, 0.8)',
      tertiary: 'rgba(255, 255, 255, 0.6)',
      disabled: 'rgba(255, 255, 255, 0.4)',
      onGlass: 'rgba(255, 255, 255, 0.9)',
    },

    // Border colors
    border: {
      primary: 'rgba(255, 255, 255, 0.1)',
      secondary: 'rgba(255, 255, 255, 0.05)',
      accent: 'rgba(150, 179, 150, 0.3)',
      glass: 'rgba(255, 255, 255, 0.08)',
    },

    // Status colors
    status: {
      green: {
        solid: '#10b981',
        glass: 'rgba(16, 185, 129, 0.15)',
        glow: 'rgba(16, 185, 129, 0.3)',
        pulse: 'rgba(16, 185, 129, 0.5)',
      },
      amber: {
        solid: '#f59e0b',
        glass: 'rgba(245, 158, 11, 0.15)',
        glow: 'rgba(245, 158, 11, 0.3)',
        pulse: 'rgba(245, 158, 11, 0.5)',
      },
      red: {
        solid: '#ef4444',
        glass: 'rgba(239, 68, 68, 0.15)',
        glow: 'rgba(239, 68, 68, 0.3)',
        pulse: 'rgba(239, 68, 68, 0.5)',
      },
      info: {
        solid: '#3b82f6',
        glass: 'rgba(59, 130, 246, 0.15)',
        glow: 'rgba(59, 130, 246, 0.3)',
        pulse: 'rgba(59, 130, 246, 0.5)',
      },
    },
  },

  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem',
  },

  borderRadius: {
    sm: '0.125rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    '2xl': '1rem',
    '3xl': '1.5rem',
    glass: '1rem',
    full: '9999px',
  },

  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    glass: {
      light: '0 8px 32px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.1)',
      medium: '0 16px 64px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1)',
      heavy: '0 32px 96px rgba(0, 0, 0, 0.2), 0 4px 8px rgba(0, 0, 0, 0.1)',
    },
  },

  glow: {
    green: '0 0 20px rgba(16, 185, 129, 0.3), 0 0 40px rgba(16, 185, 129, 0.1)',
    amber: '0 0 20px rgba(245, 158, 11, 0.3), 0 0 40px rgba(245, 158, 11, 0.1)',
    red: '0 0 20px rgba(239, 68, 68, 0.3), 0 0 40px rgba(239, 68, 68, 0.1)',
    accent: '0 0 20px rgba(150, 179, 150, 0.3), 0 0 40px rgba(150, 179, 150, 0.1)',
  },

  backdropFilter: {
    sm: 'blur(4px)',
    md: 'blur(8px)',
    lg: 'blur(12px)',
    xl: 'blur(16px)',
    '2xl': 'blur(24px)',
    '3xl': 'blur(32px)',
    glass: {
      light: 'blur(8px) saturate(1.2) brightness(1.1)',
      medium: 'blur(12px) saturate(1.3) brightness(1.05)',
      heavy: 'blur(16px) saturate(1.4) brightness(1.0)',
    },
  },

  transitions: {
    fast: '150ms ease-in-out',
    normal: '300ms ease-in-out',
    slow: '500ms ease-in-out',
    glass: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  },

  zIndex: {
    dropdown: 1000,
    sticky: 1020,
    overlay: 1040,
    modal: 1050,
    toast: 1080,
    tooltip: 1090,
  },
}

export default tokens