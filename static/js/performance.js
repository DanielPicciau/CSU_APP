/**
 * CSU Tracker - Performance Optimizations & Smooth Interactions
 * ==============================================================
 * Handles lazy loading, smooth scrolling, animations, and optimized DOM updates
 */

(function() {
  'use strict';

  // ==========================================================================
  // PERFORMANCE UTILITIES
  // ==========================================================================

  const Performance = {
    /**
     * Debounce function execution
     */
    debounce(func, wait = 100) {
      let timeout;
      return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
      };
    },

    /**
     * Throttle function execution
     */
    throttle(func, limit = 16) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    /**
     * Request idle callback polyfill
     */
    requestIdleCallback(callback) {
      if ('requestIdleCallback' in window) {
        return window.requestIdleCallback(callback);
      }
      return setTimeout(() => callback({ didTimeout: false, timeRemaining: () => 50 }), 1);
    },

    /**
     * Batch DOM updates using requestAnimationFrame
     */
    batchDOMUpdates(updates) {
      requestAnimationFrame(() => {
        updates.forEach(update => update());
      });
    }
  };

  // ==========================================================================
  // INTERSECTION OBSERVER FOR SCROLL ANIMATIONS
  // ==========================================================================

  const ScrollAnimations = {
    observer: null,

    init() {
      if (!('IntersectionObserver' in window)) return;

      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              entry.target.classList.add('is-visible');
              // Unobserve after animating (performance optimization)
              this.observer.unobserve(entry.target);
            }
          });
        },
        {
          threshold: 0.1,
          rootMargin: '0px 0px -50px 0px'
        }
      );

      // Observe all scroll-animate elements
      document.querySelectorAll('.scroll-animate').forEach(el => {
        this.observer.observe(el);
      });
    },

    // Add new element to observe
    observe(element) {
      if (this.observer && element) {
        this.observer.observe(element);
      }
    }
  };

  // ==========================================================================
  // SMOOTH PAGE TRANSITIONS
  // ==========================================================================

  const PageTransitions = {
    init() {
      // Apply entrance animation to main content
      const mainContent = document.querySelector('main > .fade-in, main > div:first-child');
      if (mainContent) {
        mainContent.classList.add('animate-fade-in-up');
      }

      // Handle link clicks for smooth transitions
      document.addEventListener('click', (e) => {
        const link = e.target.closest('a[href^="/"]');
        if (link && !link.hasAttribute('data-no-transition')) {
          this.handleLinkClick(e, link);
        }
      });
    },

    handleLinkClick(e, link) {
      // Skip for special keys or external links
      if (e.ctrlKey || e.metaKey || e.shiftKey) return;
      
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.includes('://')) return;

      // Add exit animation class
      const content = document.querySelector('main');
      if (content) {
        content.style.opacity = '0.7';
        content.style.transform = 'translateY(-10px)';
        content.style.transition = 'opacity 0.15s ease, transform 0.15s ease';
      }
    }
  };

  // ==========================================================================
  // OPTIMIZED TOUCH INTERACTIONS
  // ==========================================================================

  const TouchOptimizations = {
    init() {
      // Passive event listeners for scroll performance
      this.setupPassiveScrolling();
      
      // Optimized touch feedback
      this.setupTouchFeedback();
      
      // Prevent 300ms tap delay
      this.setupFastClick();
    },

    setupPassiveScrolling() {
      // Add passive flag to scroll/touch events for better performance
      const passiveSupported = this.checkPassiveSupport();
      const options = passiveSupported ? { passive: true } : false;

      document.addEventListener('touchstart', () => {}, options);
      document.addEventListener('touchmove', () => {}, options);
      document.addEventListener('wheel', () => {}, options);
    },

    checkPassiveSupport() {
      let passiveSupported = false;
      try {
        const options = {
          get passive() {
            passiveSupported = true;
            return false;
          }
        };
        window.addEventListener('test', null, options);
        window.removeEventListener('test', null, options);
      } catch (err) {
        passiveSupported = false;
      }
      return passiveSupported;
    },

    setupTouchFeedback() {
      // Add touch feedback to interactive elements
      const interactiveElements = document.querySelectorAll(
        'button, a, .radio-card, .btn, [role="button"]'
      );

      interactiveElements.forEach(el => {
        el.classList.add('touch-action-manipulation', 'btn-press');
      });
    },

    setupFastClick() {
      // CSS touch-action: manipulation handles this in modern browsers
      document.documentElement.style.touchAction = 'manipulation';
    }
  };

  // ==========================================================================
  // LAZY LOADING IMAGES
  // ==========================================================================

  const LazyLoading = {
    observer: null,

    init() {
      if (!('IntersectionObserver' in window)) {
        // Fallback: load all images immediately
        this.loadAllImages();
        return;
      }

      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              this.loadImage(entry.target);
              this.observer.unobserve(entry.target);
            }
          });
        },
        {
          rootMargin: '100px 0px'
        }
      );

      document.querySelectorAll('img[data-src], [data-bg]').forEach(el => {
        this.observer.observe(el);
      });
    },

    loadImage(el) {
      if (el.dataset.src) {
        el.src = el.dataset.src;
        el.removeAttribute('data-src');
      }
      if (el.dataset.bg) {
        el.style.backgroundImage = `url(${el.dataset.bg})`;
        el.removeAttribute('data-bg');
      }
      el.classList.add('loaded');
    },

    loadAllImages() {
      document.querySelectorAll('img[data-src]').forEach(img => {
        img.src = img.dataset.src;
      });
    }
  };

  // ==========================================================================
  // ANIMATED COUNTERS
  // ==========================================================================

  const AnimatedCounters = {
    init() {
      document.querySelectorAll('[data-count]').forEach(el => {
        this.animateCounter(el);
      });
    },

    animateCounter(element) {
      const target = parseInt(element.dataset.count, 10);
      const duration = parseInt(element.dataset.duration, 10) || 1000;
      const start = 0;
      const startTime = performance.now();

      const updateCounter = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Ease out cubic for smooth deceleration
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(start + (target - start) * eased);
        
        element.textContent = current;
        
        if (progress < 1) {
          requestAnimationFrame(updateCounter);
        } else {
          element.textContent = target;
        }
      };

      requestAnimationFrame(updateCounter);
    }
  };

  // ==========================================================================
  // CHART BAR ANIMATIONS
  // ==========================================================================

  const ChartAnimations = {
    init() {
      const chartBars = document.querySelectorAll('.chart-bar, [data-chart-bar]');
      if (chartBars.length === 0) return;

      // Use Intersection Observer to trigger animation when visible
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
              // Stagger the animations
              setTimeout(() => {
                entry.target.classList.add('animate-bar-grow');
                entry.target.style.transform = 'scaleY(1)';
              }, index * 50);
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.2 }
      );

      chartBars.forEach(bar => {
        bar.style.transform = 'scaleY(0)';
        bar.style.transformOrigin = 'bottom';
        bar.style.transition = 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
        observer.observe(bar);
      });
    }
  };

  // ==========================================================================
  // STAGGERED LIST ANIMATIONS
  // ==========================================================================

  const StaggeredLists = {
    init() {
      document.querySelectorAll('.stagger-animation').forEach(list => {
        this.animateList(list);
      });
    },

    animateList(list) {
      const items = list.children;
      Array.from(items).forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(20px)';
        
        requestAnimationFrame(() => {
          setTimeout(() => {
            item.style.transition = 'opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
          }, index * 50);
        });
      });
    }
  };

  // ==========================================================================
  // FORM ENHANCEMENTS
  // ==========================================================================

  const FormEnhancements = {
    init() {
      // Radio card animations
      this.setupRadioCards();
      
      // Input focus animations
      this.setupInputAnimations();
      
      // Form submission feedback
      this.setupFormSubmission();
    },

    setupRadioCards() {
      document.querySelectorAll('.radio-card').forEach(card => {
        card.classList.add('radio-card-animated');
        
        const input = card.querySelector('input[type="radio"]');
        if (input) {
          input.addEventListener('change', () => {
            // Remove active class from siblings
            const parent = card.parentElement;
            parent.querySelectorAll('.radio-card').forEach(c => {
              c.classList.remove('selected');
            });
            
            // Add to selected
            card.classList.add('selected');
            
            // Add pulse animation
            card.style.animation = 'selectionPulse 0.4s ease';
            setTimeout(() => {
              card.style.animation = '';
            }, 400);
          });
        }
      });
    },

    setupInputAnimations() {
      document.querySelectorAll('input, textarea, select').forEach(input => {
        if (!input.classList.contains('input-animated')) {
          input.classList.add('input-animated');
        }
      });
    },

    setupFormSubmission() {
      document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
          const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
          if (submitBtn && !submitBtn.disabled) {
            // Add loading state
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner spinner-sm"></span> Saving...';
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-75');
            
            // Re-enable after a timeout (in case of error)
            setTimeout(() => {
              if (submitBtn.disabled) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-75');
              }
            }, 10000);
          }
        });
      });
    }
  };

  // ==========================================================================
  // SCORE DISPLAY ANIMATIONS
  // ==========================================================================

  const ScoreAnimations = {
    init() {
      // Animate score circles on page load
      document.querySelectorAll('.score-circle, [data-score]').forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'scale(0)';
        
        setTimeout(() => {
          el.style.transition = 'opacity 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';
          el.style.opacity = '1';
          el.style.transform = 'scale(1)';
        }, 200 + (index * 100));
      });
    }
  };

  // ==========================================================================
  // PREFETCHING FOR FASTER NAVIGATION
  // ==========================================================================

  const Prefetching = {
    prefetchedUrls: new Set(),

    init() {
      // Prefetch links on hover for faster navigation
      document.addEventListener('mouseover', Performance.debounce((e) => {
        const link = e.target.closest('a[href^="/"]');
        if (link) {
          this.prefetchUrl(link.href);
        }
      }, 100));

      // Also prefetch on touchstart for mobile
      document.addEventListener('touchstart', (e) => {
        const link = e.target.closest('a[href^="/"]');
        if (link) {
          this.prefetchUrl(link.href);
        }
      }, { passive: true });
    },

    prefetchUrl(url) {
      if (this.prefetchedUrls.has(url)) return;
      if (url.includes('/api/') || url.includes('/logout')) return;

      this.prefetchedUrls.add(url);

      // Use link prefetch for supported browsers
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      link.as = 'document';
      document.head.appendChild(link);
    }
  };

  // ==========================================================================
  // SMOOTH SCROLL
  // ==========================================================================

  const SmoothScroll = {
    init() {
      // Enable smooth scrolling for anchor links
      document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
          const targetId = anchor.getAttribute('href');
          if (targetId === '#') return;

          const target = document.querySelector(targetId);
          if (target) {
            e.preventDefault();
            target.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }
        });
      });
    }
  };

  // ==========================================================================
  // MEMORY OPTIMIZATION
  // ==========================================================================

  const MemoryOptimization = {
    init() {
      // Clean up animations when they complete
      document.addEventListener('animationend', (e) => {
        if (e.target.classList.contains('animate-fade-in-up') ||
            e.target.classList.contains('animate-fade-in-scale')) {
          e.target.style.willChange = 'auto';
        }
      });

      // Reduce animations when page is hidden
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          document.body.classList.add('reduce-motion');
        } else {
          document.body.classList.remove('reduce-motion');
        }
      });
    }
  };

  // ==========================================================================
  // BOTTOM NAV ANIMATIONS
  // ==========================================================================

  const BottomNavAnimations = {
    init() {
      const navItems = document.querySelectorAll('nav a');
      
      navItems.forEach(item => {
        item.addEventListener('click', function() {
          // Add bounce animation to the icon
          const icon = this.querySelector('svg');
          if (icon) {
            icon.classList.add('nav-icon-active');
            setTimeout(() => icon.classList.remove('nav-icon-active'), 400);
          }
        });
      });
    }
  };

  // ==========================================================================
  // INITIALIZE ALL MODULES
  // ==========================================================================

  function init() {
    // Initialize immediately
    TouchOptimizations.init();
    PageTransitions.init();
    BottomNavAnimations.init();
    
    // Initialize after DOM is interactive
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initDOMDependentModules);
    } else {
      initDOMDependentModules();
    }
  }

  function initDOMDependentModules() {
    ScrollAnimations.init();
    FormEnhancements.init();
    ScoreAnimations.init();
    ChartAnimations.init();
    StaggeredLists.init();
    SmoothScroll.init();
    MemoryOptimization.init();
    
    // Initialize less critical features during idle time
    Performance.requestIdleCallback(() => {
      LazyLoading.init();
      Prefetching.init();
      AnimatedCounters.init();
    });
  }

  // Expose utilities globally for external use
  window.CSUPerformance = {
    Performance,
    ScrollAnimations,
    AnimatedCounters,
    StaggeredLists
  };

  // Initialize
  init();

})();
