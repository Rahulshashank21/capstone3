# Frontend Guidelines (frontend/CLAUDE.md)

## Purpose & Scope
Provides the user interface for TelcoLane, enabling subscribers to self-register, manage plans, preview pro-rata costs, track port-out cooling periods, and allowing CSRs and Admins to manage overrides and view analytics dashboards.

## Core Rules
1. **Responsive Viewports**: Responsive layout supporting mobile (< 768px), tablet (768-1024px), and desktop (> 1024px).
2. **PII Masking**: Ensure mobile numbers are shown masked (`XXXXXX1234`) on customer-facing screens.
3. **Pro-Rata Preview**: Before confirming any mid-cycle plan migration, show an explicit breakdown of old plan credit, new plan charge, and net total.
4. **Accessible UI Controls**: Use clear labels, contrasting colors, error callouts, and keyboard-accessible buttons.
