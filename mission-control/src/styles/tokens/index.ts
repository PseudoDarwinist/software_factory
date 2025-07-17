/**
 * Design System Tokens for Mission Control
 * 
 * This file contains all design tokens used throughout the application.
 * These tokens implement the "Jony Ive on Acid" aesthetic with liquid glass morphism.
 * 
 * Why tokens exist:
 * - Consistent design language across all components
 * - Easy theme switching and customization
 * - Maintainable design system
 * - AI-friendly design patterns
 * 
 * For AI agents: Use these tokens instead of hard-coded values when styling components.
 * All visual design should reference these semantic tokens.
 */

// ========================================
// Color Tokens - Liquid Glass Theme
// ========================================

export const colors = {
  // Base colors
  black: '#000000',
  white: '#ffffff',
  transparent: 'transparent',
  
  // Glass morphism base
  glass: {
    primary: 'rgba(150, 179, 150, 0.15)',      // Primary green glass
    secondary: 'rgba(150, 179, 150, 0.08)',    // Subtle green glass
    accent: 'rgba(150, 179, 150, 0.25)',       // Accent green glass
    neutral: 'rgba(255, 255, 255, 0.05)',      // Neutral glass
    dark: 'rgba(0, 0, 0, 0.2)',                // Dark glass overlay
  },
  
  // Surface colors
  surface: {
    primary: '#0a0a0a',                         // Main background
    secondary: '#1a1a1a',                       // Card backgrounds
    tertiary: '#2a2a2a',                        // Elevated surfaces
    quaternary: '#3a3a3a',                      // Highest elevation
    glass: 'rgba(255, 255, 255, 0.02)',        // Glass surface
    glassHover: 'rgba(255, 255, 255, 0.05)',   // Glass on hover
    glassActive: 'rgba(255, 255, 255, 0.08)',  // Glass when active
  },
  
  // Text colors
  text: {
    primary: '#ffffff',                         // Primary text
    secondary: 'rgba(255, 255, 255, 0.8)',     // Secondary text
    tertiary: 'rgba(255, 255, 255, 0.6)',      // Tertiary text
    disabled: 'rgba(255, 255, 255, 0.4)',      // Disabled text
    onGlass: 'rgba(255, 255, 255, 0.9)',       // Text on glass surfaces
  },
  
  // Border colors
  border: {
    primary: 'rgba(255, 255, 255, 0.1)',       // Primary borders
    secondary: 'rgba(255, 255, 255, 0.05)',    // Subtle borders
    accent: 'rgba(150, 179, 150, 0.3)',        // Accent borders
    glass: 'rgba(255, 255, 255, 0.08)',        // Glass borders
  },
  
  // Status colors with glass treatment
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
  
  // Accent colors
  accent: {
    primary: '#96b396',                         // Primary accent
    secondary: '#7d947d',                       // Secondary accent
    tertiary: '#647564',                        // Tertiary accent
    glow: 'rgba(150, 179, 150, 0.4)',         // Glow effect
    neon: 'rgba(150, 179, 150, 0.8)',         // Neon effect
  },
}

// ========================================
// Typography Tokens
// ========================================

export const typography = {
  fontFamily: {
    primary: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: 'Menlo, Monaco, "Courier New", monospace',
  },
  
  fontSize: {
    xs: '0.75rem',      // 12px
    sm: '0.875rem',     // 14px
    base: '1rem',       // 16px
    lg: '1.125rem',     // 18px
    xl: '1.25rem',      // 20px
    '2xl': '1.5rem',    // 24px
    '3xl': '1.875rem',  // 30px
    '4xl': '2.25rem',   // 36px
    '5xl': '3rem',      // 48px
    '6xl': '3.75rem',   // 60px
  },
  
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  
  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
  
  letterSpacing: {
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
  },
}

// ========================================
// Spacing Tokens
// ========================================

export const spacing = {
  px: '1px',
  0: '0',
  1: '0.25rem',    // 4px
  2: '0.5rem',     // 8px
  3: '0.75rem',    // 12px
  4: '1rem',       // 16px
  5: '1.25rem',    // 20px
  6: '1.5rem',     // 24px
  8: '2rem',       // 32px
  10: '2.5rem',    // 40px
  12: '3rem',      // 48px
  16: '4rem',      // 64px
  20: '5rem',      // 80px
  24: '6rem',      // 96px
  32: '8rem',      // 128px
  40: '10rem',     // 160px
  48: '12rem',     // 192px
  56: '14rem',     // 224px
  64: '16rem',     // 256px
}

// ========================================
// Border Radius Tokens
// ========================================

export const borderRadius = {
  none: '0',
  sm: '0.125rem',    // 2px
  md: '0.375rem',    // 6px
  lg: '0.5rem',      // 8px
  xl: '0.75rem',     // 12px
  '2xl': '1rem',     // 16px
  '3xl': '1.5rem',   // 24px
  full: '9999px',
  glass: '1rem',     // Standard glass morphism radius
}

// ========================================
// Shadow Tokens - Liquid Glass Effects
// ========================================

export const shadows = {
  // Standard shadows
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  
  // Glass morphism shadows
  glass: {
    light: '0 8px 32px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.1)',
    medium: '0 16px 64px rgba(0, 0, 0, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1)',
    heavy: '0 32px 96px rgba(0, 0, 0, 0.2), 0 4px 8px rgba(0, 0, 0, 0.1)',
  },
  
  // Glow effects
  glow: {
    green: '0 0 20px rgba(16, 185, 129, 0.3), 0 0 40px rgba(16, 185, 129, 0.1)',
    amber: '0 0 20px rgba(245, 158, 11, 0.3), 0 0 40px rgba(245, 158, 11, 0.1)',
    red: '0 0 20px rgba(239, 68, 68, 0.3), 0 0 40px rgba(239, 68, 68, 0.1)',
    accent: '0 0 20px rgba(150, 179, 150, 0.3), 0 0 40px rgba(150, 179, 150, 0.1)',
  },
  
  // Inset shadows for depth
  inset: {
    light: 'inset 0 2px 4px rgba(0, 0, 0, 0.1)',
    medium: 'inset 0 4px 8px rgba(0, 0, 0, 0.15)',
    heavy: 'inset 0 8px 16px rgba(0, 0, 0, 0.2)',
  },
}

// ========================================
// Animation Tokens
// ========================================

export const animations = {
  // Durations
  duration: {
    instant: '0ms',
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
    slower: '750ms',
    slowest: '1000ms',
  },
  
  // Easing functions
  easing: {
    linear: 'linear',
    ease: 'ease',
    easeIn: 'ease-in',
    easeOut: 'ease-out',
    easeInOut: 'ease-in-out',
    spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
    glass: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },
  
  // Transforms
  transform: {
    scale: {
      95: 'scale(0.95)',
      105: 'scale(1.05)',
      110: 'scale(1.1)',
    },
    rotate: {
      1: 'rotate(1deg)',
      2: 'rotate(2deg)',
      3: 'rotate(3deg)',
    },
  },
}

// ========================================
// Backdrop Filter Tokens
// ========================================

export const backdropFilters = {
  blur: {
    sm: 'blur(4px)',
    md: 'blur(8px)',
    lg: 'blur(12px)',
    xl: 'blur(16px)',
    '2xl': 'blur(24px)',
    '3xl': 'blur(32px)',
  },
  
  saturate: {
    50: 'saturate(0.5)',
    100: 'saturate(1)',
    150: 'saturate(1.5)',
    200: 'saturate(2)',
  },
  
  brightness: {
    50: 'brightness(0.5)',
    90: 'brightness(0.9)',
    100: 'brightness(1)',
    110: 'brightness(1.1)',
    125: 'brightness(1.25)',
  },
  
  // Combined glass effects
  glass: {
    light: 'blur(8px) saturate(1.2) brightness(1.1)',
    medium: 'blur(12px) saturate(1.3) brightness(1.05)',
    heavy: 'blur(16px) saturate(1.4) brightness(1.0)',
  },
}

// ========================================
// Z-Index Tokens
// ========================================

export const zIndex = {
  hide: -1,
  base: 0,
  docked: 10,
  dropdown: 1000,
  sticky: 1020,
  banner: 1030,
  overlay: 1040,
  modal: 1050,
  popover: 1060,
  skipLink: 1070,
  toast: 1080,
  tooltip: 1090,
}

// ========================================
// Breakpoints
// ========================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
}

// ========================================
// Component-Specific Tokens
// ========================================

export const components = {
  // Card tokens
  card: {
    padding: spacing[6],
    borderRadius: borderRadius.glass,
    background: colors.surface.glass,
    backdropFilter: backdropFilters.glass.medium,
    border: `1px solid ${colors.border.glass}`,
    shadow: shadows.glass.light,
  },
  
  // Button tokens
  button: {
    padding: {
      sm: `${spacing[2]} ${spacing[4]}`,
      md: `${spacing[3]} ${spacing[6]}`,
      lg: `${spacing[4]} ${spacing[8]}`,
    },
    borderRadius: borderRadius.lg,
    transition: `all ${animations.duration.normal} ${animations.easing.glass}`,
  },
  
  // Input tokens
  input: {
    padding: spacing[3],
    borderRadius: borderRadius.md,
    background: colors.surface.glass,
    border: `1px solid ${colors.border.primary}`,
    transition: `all ${animations.duration.fast} ${animations.easing.glass}`,
  },
  
  // Health dot tokens
  healthDot: {
    size: spacing[3],
    pulseScale: '1.4',
    pulseDuration: animations.duration.slowest,
    glowIntensity: '0.6',
  },
}

// ========================================
// Export All Tokens
// ========================================

export const tokens = {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  animations,
  backdropFilters,
  zIndex,
  breakpoints,
  components,
}

export default tokens