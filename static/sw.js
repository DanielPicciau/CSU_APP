// CSU Tracker Service Worker - Safari Compatible
const CACHE_VERSION = 'v5';
const STATIC_CACHE = `csu-static-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/';

// ONLY cache truly static assets (never HTML pages that might redirect)
const STATIC_ASSETS = [
    '/offline/',
    '/static/icons/icon-192x192.png',
    '/static/icons/apple-touch-icon.png',
    '/static/css/animations.css',
    '/static/css/design-tokens.css',
    '/static/css/components.css',
    '/static/js/performance.js',
    '/static/js/instant-nav.js',
    '/static/js/offline-storage.js',
    '/static/js/htmx.min.js',
];

// Install event - cache only static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing version:', CACHE_VERSION);
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Pre-caching static assets');
                return Promise.allSettled(
                    STATIC_ASSETS.map(url => 
                        fetch(url).then(response => {
                            if (response.ok && !response.redirected) {
                                return cache.put(url, response);
                            }
                        }).catch(() => {
                            console.log('[SW] Failed to cache:', url);
                        })
                    )
                );
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up ALL old caches aggressively
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating version:', CACHE_VERSION);
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== STATIC_CACHE)
                    .map((name) => {
                        console.log('[SW] Deleting cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => {
            console.log('[SW] Claiming clients');
            return self.clients.claim();
        })
    );
});

// Fetch event - NEVER cache HTML/navigation, only static assets
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') return;
    
    // Skip cross-origin requests
    if (url.origin !== location.origin) return;
    
    // NEVER intercept navigation requests - let them go to network
    // This prevents the Safari redirect caching issue
    if (request.mode === 'navigate') {
        return;
    }
    
    // NEVER intercept HTML requests
    if (request.headers.get('accept')?.includes('text/html')) {
        return;
    }
    
    // API requests - always network
    if (url.pathname.includes('/api/')) {
        return;
    }
    
    // Only handle static assets
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }
                return fetch(request).then((networkResponse) => {
                    if (networkResponse.ok && !networkResponse.redirected) {
                        const responseClone = networkResponse.clone();
                        caches.open(STATIC_CACHE).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return networkResponse;
                });
            }).catch(() => {
                return new Response('', { status: 404 });
            })
        );
        return;
    }
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('[SW] Push received:', event);
    
    let data = {
        title: 'CSU Tracker',
        body: 'Time to log your daily score!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: 'csu-reminder',
        data: { url: '/tracking/log/' }
    };
    
    if (event.data) {
        try {
            const payload = event.data.json();
            data = { ...data, ...payload };
        } catch (e) {
            console.error('[SW] Failed to parse push data:', e);
        }
    }
    
    const options = {
        body: data.body,
        icon: data.icon,
        badge: data.badge,
        tag: data.tag,
        data: data.data,
        vibrate: [100, 50, 100],
        requireInteraction: true,
        actions: [
            { action: 'log', title: 'Log Now' },
            { action: 'dismiss', title: 'Later' }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event);
    
    event.notification.close();
    
    const action = event.action;
    let url = '/tracking/log/';
    
    if (action === 'log' || !action) {
        url = event.notification.data?.url || '/tracking/log/';
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.navigate(url);
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
    console.log('[SW] Notification closed:', event);
});
