/**
 * CSU Tracker - Instant Navigation System
 * ========================================
 * Makes page transitions feel instant using:
 * - Link prefetching on hover/touch
 * - View Transitions API for smooth animations
 * - Skeleton screens during navigation
 * - Background preloading of likely next pages
 */

(function() {
  'use strict';

  const InstantNav = {
    // Prefetch cache to avoid duplicate requests
    prefetchCache: new Set(),
    
    // Pages to preload in background after initial load
    preloadPriority: ['/tracking/today/', '/tracking/log/', '/tracking/history/'],
    
    // Minimum delay before showing skeleton (prevents flicker on fast loads)
    SKELETON_DELAY_MS: 50,
    
    // How long to wait on hover before prefetching
    PREFETCH_DELAY_MS: 65,

    init() {
      this.setupLinkPrefetching();
      this.setupViewTransitions();
      this.setupSkeletonScreens();
      this.preloadPriorityPages();
      this.setupNavigationTiming();
    },

    /**
     * Prefetch pages on hover/touch start
     */
    setupLinkPrefetching() {
      let hoverTimeout = null;
      
      document.addEventListener('mouseover', (e) => {
        const link = e.target.closest('a[href]');
        if (!link || !this.shouldPrefetch(link)) return;
        
        // Delay prefetch slightly to avoid prefetching on quick mouse movements
        hoverTimeout = setTimeout(() => {
          this.prefetchPage(link.href);
        }, this.PREFETCH_DELAY_MS);
      });
      
      document.addEventListener('mouseout', (e) => {
        if (hoverTimeout) {
          clearTimeout(hoverTimeout);
          hoverTimeout = null;
        }
      });
      
      // Prefetch immediately on touch start (mobile)
      document.addEventListener('touchstart', (e) => {
        const link = e.target.closest('a[href]');
        if (link && this.shouldPrefetch(link)) {
          this.prefetchPage(link.href);
        }
      }, { passive: true });
      
      // Also prefetch on focus (keyboard navigation)
      document.addEventListener('focusin', (e) => {
        const link = e.target.closest('a[href]');
        if (link && this.shouldPrefetch(link)) {
          this.prefetchPage(link.href);
        }
      });
    },

    /**
     * Check if a link should be prefetched
     */
    shouldPrefetch(link) {
      // Skip if already prefetched
      if (this.prefetchCache.has(link.href)) return false;
      
      // Skip external links
      if (link.origin !== location.origin) return false;
      
      // Skip hash links
      if (link.href.includes('#') && link.pathname === location.pathname) return false;
      
      // Skip non-GET links (forms, etc)
      if (link.hasAttribute('data-no-prefetch')) return false;
      
      // Skip static assets
      if (link.pathname.startsWith('/static/')) return false;
      
      // Skip API endpoints
      if (link.pathname.startsWith('/api/')) return false;
      
      // Skip admin
      if (link.pathname.startsWith('/admin/')) return false;
      
      // Skip auth pages (login, register, password reset) - these have rate limits
      if (link.pathname.startsWith('/accounts/login')) return false;
      if (link.pathname.startsWith('/accounts/register')) return false;
      if (link.pathname.startsWith('/accounts/password-reset')) return false;
      if (link.pathname.startsWith('/accounts/logout')) return false;
      
      return true;
    },

    /**
     * Prefetch a page into browser cache
     */
    prefetchPage(url) {
      if (this.prefetchCache.has(url)) return;
      this.prefetchCache.add(url);
      
      // Use link prefetch for best browser support
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      link.as = 'document';
      document.head.appendChild(link);
      
      // Also do a low-priority fetch for more aggressive caching
      if ('fetch' in window) {
        fetch(url, {
          priority: 'low',
          credentials: 'same-origin',
          headers: { 'X-Prefetch': '1' }
        }).catch(() => {}); // Ignore errors
      }
    },

    /**
     * Setup View Transitions API for smooth page changes
     * NOTE: Disabled for now - the partial content swap breaks page state.
     * Instead, we use prefetching + skeleton screens for perceived performance.
     */
    setupViewTransitions() {
      // View transitions disabled - using fallback transitions only
      // The prefetching already makes pages feel instant
      this.setupFallbackTransitions();
    },

    /**
     * Fallback transitions for browsers without View Transitions API
     */
    setupFallbackTransitions() {
      document.addEventListener('click', (e) => {
        const link = e.target.closest('a[href]');
        if (!link || !this.shouldTransition(link)) return;
        
        // Show skeleton before navigation
        this.showSkeleton();
        
        // Let the click proceed naturally
      });
      
      // Hide skeleton on page load (for back/forward navigation)
      window.addEventListener('pageshow', () => {
        this.hideSkeleton();
      });
    },

    /**
     * Check if a link should use view transitions
     */
    shouldTransition(link) {
      // Same checks as prefetch
      if (link.origin !== location.origin) return false;
      if (link.hasAttribute('data-no-transition')) return false;
      if (link.pathname.startsWith('/static/')) return false;
      if (link.pathname.startsWith('/api/')) return false;
      if (link.pathname.startsWith('/admin/')) return false;
      if (link.target === '_blank') return false;
      
      // Skip form submissions
      if (link.closest('form')) return false;
      
      return true;
    },

    /**
     * Setup skeleton screen system
     */
    setupSkeletonScreens() {
      // Create skeleton overlay
      const skeleton = document.createElement('div');
      skeleton.id = 'nav-skeleton';
      skeleton.className = 'nav-skeleton';
      skeleton.innerHTML = `
        <div class="skeleton-content">
          <div class="skeleton-header"></div>
          <div class="skeleton-card"></div>
          <div class="skeleton-card skeleton-card--short"></div>
          <div class="skeleton-stats">
            <div class="skeleton-stat"></div>
            <div class="skeleton-stat"></div>
            <div class="skeleton-stat"></div>
          </div>
        </div>
      `;
      skeleton.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: var(--bg-primary, #fafafa);
        z-index: 9999;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.15s ease;
        padding: calc(env(safe-area-inset-top, 0px) + 60px) 16px 16px;
      `;
      document.body.appendChild(skeleton);
      
      // Add skeleton styles
      const style = document.createElement('style');
      style.textContent = `
        .nav-skeleton.visible {
          opacity: 1;
          pointer-events: auto;
        }
        .skeleton-content {
          max-width: 600px;
          margin: 0 auto;
        }
        .skeleton-header {
          height: 32px;
          width: 60%;
          background: linear-gradient(90deg, var(--bg-tertiary, #e5e5e5) 25%, var(--bg-secondary, #f5f5f5) 50%, var(--bg-tertiary, #e5e5e5) 75%);
          background-size: 200% 100%;
          animation: skeleton-shimmer 1.5s infinite;
          border-radius: 8px;
          margin-bottom: 24px;
        }
        .skeleton-card {
          height: 180px;
          background: linear-gradient(90deg, var(--bg-tertiary, #e5e5e5) 25%, var(--bg-secondary, #f5f5f5) 50%, var(--bg-tertiary, #e5e5e5) 75%);
          background-size: 200% 100%;
          animation: skeleton-shimmer 1.5s infinite;
          border-radius: 16px;
          margin-bottom: 16px;
        }
        .skeleton-card--short {
          height: 100px;
        }
        .skeleton-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          margin-top: 24px;
        }
        .skeleton-stat {
          height: 80px;
          background: linear-gradient(90deg, var(--bg-tertiary, #e5e5e5) 25%, var(--bg-secondary, #f5f5f5) 50%, var(--bg-tertiary, #e5e5e5) 75%);
          background-size: 200% 100%;
          animation: skeleton-shimmer 1.5s infinite;
          border-radius: 12px;
        }
        @keyframes skeleton-shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @media (prefers-color-scheme: dark) {
          .skeleton-header, .skeleton-card, .skeleton-stat {
            background: linear-gradient(90deg, #1a1a1a 25%, #2a2a2a 50%, #1a1a1a 75%);
            background-size: 200% 100%;
          }
        }
      `;
      document.head.appendChild(style);
    },

    showSkeleton() {
      const skeleton = document.getElementById('nav-skeleton');
      if (skeleton) {
        // Small delay to prevent flicker on fast loads
        this._skeletonTimeout = setTimeout(() => {
          skeleton.classList.add('visible');
        }, this.SKELETON_DELAY_MS);
      }
    },

    hideSkeleton() {
      clearTimeout(this._skeletonTimeout);
      const skeleton = document.getElementById('nav-skeleton');
      if (skeleton) {
        skeleton.classList.remove('visible');
      }
    },

    /**
     * Preload priority pages in background
     */
    preloadPriorityPages() {
      // Wait for page to be fully loaded and idle
      if ('requestIdleCallback' in window) {
        requestIdleCallback(() => {
          this.preloadPriority.forEach(url => {
            if (url !== location.pathname) {
              this.prefetchPage(url);
            }
          });
        }, { timeout: 3000 });
      } else {
        setTimeout(() => {
          this.preloadPriority.forEach(url => {
            if (url !== location.pathname) {
              this.prefetchPage(url);
            }
          });
        }, 2000);
      }
    },

    /**
     * Update active navigation state
     */
    updateActiveNav(url) {
      const pathname = new URL(url, location.origin).pathname;
      
      document.querySelectorAll('.nav-item, .desktop-nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href === pathname || (pathname === '/' && href.includes('today'))) {
          item.classList.add('active');
        } else {
          item.classList.remove('active');
        }
      });
    },

    /**
     * Performance timing for debugging
     */
    setupNavigationTiming() {
      if (!('performance' in window)) return;
      
      // Log navigation performance
      window.addEventListener('load', () => {
        setTimeout(() => {
          const timing = performance.getEntriesByType('navigation')[0];
          if (timing) {
            console.log('[Performance] Page load:', Math.round(timing.loadEventEnd - timing.startTime), 'ms');
          }
        }, 0);
      });
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => InstantNav.init());
  } else {
    InstantNav.init();
  }

  // Expose for debugging
  window.InstantNav = InstantNav;

})();
