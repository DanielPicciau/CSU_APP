// CSU Tracker Service Worker - Safari Compatible
const CACHE_VERSION = 'v6';
const STATIC_CACHE = `csu-static-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/';

// ONLY cache truly static assets (never HTML pages that might redirect)
const STATIC_ASSETS = [
    '/offline/',
    '/static/icons/icon-192x192.png',
    '/static/icons/apple-touch-icon.png',
];

// Install event - cache only static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing version:', CACHE_VERSION);
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                return Promise.allSettled(
                    STATIC_ASSETS.map(url => 
                        fetch(url).then(response => {
                            if (response.ok && !response.redirected) {
                                return cache.put(url, response);
                            }
                        }).catch(() => console.log('[SW] Failed to cache:', url))
                    )
                );
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up ALL old caches
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
        }).then(() => self.clients.claim())
    );
});

// Fetch event - NEVER intercept navigation/HTML requests
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') return;
    
    // Skip cross-origin
    if (url.origin !== location.origin) return;
    
    // NEVER intercept navigation - prevents Safari redirect issue
    if (request.mode === 'navigate') return;
    
    // NEVER intercept HTML requests
    if (request.headers.get('accept')?.includes('text/html')) return;
    
    // Skip API
    if (url.pathname.includes('/api/')) return;
    
    // Only handle /static/ assets
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then((cached) => {
                if (cached) return cached;
                return fetch(request).then((response) => {
                    if (response.ok && !response.redirected) {
                        const clone = response.clone();
                        caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone));
                    }
                    return response;
                });
            }).catch(() => new Response('', { status: 404 }))
        );
    }
});

// Push notifications
self.addEventListener('push', (event) => {
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
            data = { ...data, ...event.data.json() };
        } catch (e) {}
    }
    
    event.waitUntil(
        self.registration.showNotification(data.title, {
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
        })
    );
});

// Notification click
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data?.url || '/tracking/log/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                for (const client of clientList) {
                    if ('focus' in client) {
                        client.navigate(url);
                        return client.focus();
                    }
                }
                if (clients.openWindow) return clients.openWindow(url);
            })
    );
});
