// CSU Tracker Service Worker - Optimized for Performance
const CACHE_VERSION = 'v2';
const STATIC_CACHE = `csu-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `csu-dynamic-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/';

// Static assets to cache immediately (critical for app shell)
const STATIC_ASSETS = [
    '/',
    '/offline/',
    '/static/icons/icon-192x192.png',
    '/static/icons/apple-touch-icon.png',
    '/static/css/animations.css',
    '/static/js/performance.js',
];

// Assets to cache opportunistically
const CACHE_ON_DEMAND = [
    '/tracking/',
    '/tracking/log/',
    '/tracking/history/',
    '/notifications/settings/',
];

// Cache size limits
const MAX_DYNAMIC_CACHE_SIZE = 50;

// Install event - cache critical static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Pre-caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => {
                        // Delete old version caches
                        return name.startsWith('csu-') && 
                               name !== STATIC_CACHE && 
                               name !== DYNAMIC_CACHE;
                    })
                    .map((name) => {
                        console.log('[SW] Deleting old cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

// Trim dynamic cache to max size
async function trimCache(cacheName, maxSize) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length > maxSize) {
        // Delete oldest entries first
        await cache.delete(keys[0]);
        return trimCache(cacheName, maxSize);
    }
}

// Strategy: Stale-While-Revalidate for HTML pages
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    // Fetch fresh copy in background
    const fetchPromise = fetch(request).then((networkResponse) => {
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
            trimCache(DYNAMIC_CACHE, MAX_DYNAMIC_CACHE_SIZE);
        }
        return networkResponse;
    }).catch(() => null);
    
    // Return cached version immediately, or wait for network
    return cachedResponse || fetchPromise;
}

// Strategy: Cache-First for static assets
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // Return offline page for navigation
        if (request.mode === 'navigate') {
            return caches.match(OFFLINE_URL);
        }
        throw error;
    }
}

// Strategy: Network-First for API and dynamic content
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        if (request.mode === 'navigate') {
            return caches.match(OFFLINE_URL);
        }
        throw error;
    }
}

// Fetch event with optimized caching strategies
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') return;
    
    // Skip cross-origin requests (except CDNs)
    if (url.origin !== location.origin && 
        !url.hostname.includes('cdn') &&
        !url.hostname.includes('unpkg')) {
        return;
    }
    
    // API requests - don't cache, always network
    if (url.pathname.includes('/api/')) {
        return;
    }
    
    // Static assets - cache first (faster)
    if (url.pathname.startsWith('/static/') || 
        url.pathname.endsWith('.js') ||
        url.pathname.endsWith('.css') ||
        url.pathname.endsWith('.png') ||
        url.pathname.endsWith('.jpg') ||
        url.pathname.endsWith('.svg') ||
        url.pathname.endsWith('.woff2')) {
        event.respondWith(cacheFirst(request));
        return;
    }
    
    // HTML pages - stale-while-revalidate (fast + fresh)
    if (request.mode === 'navigate' || 
        request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }
    
    // Everything else - network first
    event.respondWith(networkFirst(request));
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
    console.log('Push received:', event);
    
    let data = {
        title: 'CSU Tracker',
        body: 'Time to log your daily score!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: 'csu-reminder',
        data: { url: '/' }
    };
    
    if (event.data) {
        try {
            const payload = event.data.json();
            data = { ...data, ...payload };
        } catch (e) {
            console.error('Failed to parse push data:', e);
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
    console.log('Notification clicked:', event);
    
    event.notification.close();
    
    const action = event.action;
    let url = '/';
    
    if (action === 'log' || !action) {
        url = event.notification.data?.url || '/tracking/log/';
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Focus existing window if available
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.navigate(url);
                        return client.focus();
                    }
                }
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
    console.log('Notification closed:', event);
});
