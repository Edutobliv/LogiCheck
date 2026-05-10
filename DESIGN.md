---
version: "alpha"
name: LogiCheck
description: "Design tokens for the LogiCheck logistics auditing desktop app."
colors:
  primary: "#0F172A"
  surface: "#111827"
  surface-raised: "#1E293B"
  border: "#334155"
  text: "#F8FAFC"
  text-muted: "#94A3B8"
  accent: "#3B82F6"
  success: "#10B981"
  warning: "#F59E0B"
  danger: "#EF4444"
  light-bg: "#F2F3F5"
  light-surface: "#FFFFFF"
  light-text: "#1A1B26"
typography:
  title:
    fontFamily: "Segoe UI"
    fontSize: 22px
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: 0
  heading:
    fontFamily: "Segoe UI"
    fontSize: 16px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: 0
  body:
    fontFamily: "Segoe UI"
    fontSize: 13px
    fontWeight: 500
    lineHeight: 1.45
    letterSpacing: 0
  caption:
    fontFamily: "Segoe UI"
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0
rounded:
  sm: 4px
  md: 8px
  lg: 12px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 12px
  button-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 12px
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 12px
  panel:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    padding: 24px
  table-row-warning:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.primary}"
    typography: "{typography.caption}"
---

## Overview

LogiCheck should feel like an operational control room for logistics teams: dense, readable, and trustworthy. Visual weight belongs to live counts, discrepancy status, and export actions. Decorative elements should stay restrained so operators can scan results quickly during dispatch.

## Colors

Dark mode is the primary working environment, using deep navy surfaces, bright text, and a clear blue action color. Green, amber, and red are reserved for audit states: conforming results, warnings, and discrepancies.

Light mode keeps the same hierarchy with white surfaces and high-contrast text for office review, printing, and shared screens.

## Typography

Use Segoe UI across the desktop app for native Windows clarity. Headings are compact and heavy; body text stays at 13px for table density and repeated operational use.

## Layout

Navigation is stable on the left. Work pages should prioritize one primary task per view: upload invoice, analyze video, review camera counts, assign vehicle, or export reports. Tables should favor scanability over large empty spacing.

## Elevation & Depth

Use subtle shadows and borders to separate tools from the background. Avoid heavy glass effects in tables and forms where contrast matters more than atmosphere.

## Shapes

Use 8px radius for buttons and operational controls. Larger 12px radius is acceptable for top-level panels only.

## Components

Primary buttons trigger the next workflow step. Success buttons confirm completed exports or valid assignments. Danger should be limited to destructive or discrepancy-heavy states.

## Do's and Don'ts

Do keep audit status colors consistent across PDF, Excel, video, and UI exports.

Do not use large marketing hero layouts inside the desktop app. Operators should land directly on useful controls and current state.
