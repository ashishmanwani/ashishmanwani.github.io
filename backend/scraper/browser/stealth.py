"""
Playwright browser fingerprint randomization scripts.
These are injected as page.add_init_script() before any page load.
They patch the JS environment to remove headless browser signatures.
"""

import random

STEALTH_SCRIPT = """
// 1. Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// 2. Populate navigator.plugins (headless has 0 plugins)
const makePlugin = (name, desc, filename, mimeTypes) => {
    const plugin = Object.create(Plugin.prototype);
    Object.defineProperty(plugin, 'name', {value: name});
    Object.defineProperty(plugin, 'description', {value: desc});
    Object.defineProperty(plugin, 'filename', {value: filename});
    Object.defineProperty(plugin, 'length', {value: mimeTypes.length});
    return plugin;
};
const fakePlugins = [
    makePlugin('Chrome PDF Plugin', 'Portable Document Format', 'internal-pdf-viewer', ['application/x-google-chrome-pdf']),
    makePlugin('Chrome PDF Viewer', '', 'mhjfbmdgcfjbbpaeojofohoefgiehjai', ['application/pdf']),
    makePlugin('Native Client', '', 'internal-nacl-plugin', ['application/x-nacl']),
];
Object.defineProperty(navigator, 'plugins', {
    get: () => fakePlugins,
    configurable: true
});

// 3. Set realistic languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-IN', 'en-GB', 'en-US', 'en'],
    configurable: true
});

// 4. Populate window.chrome (missing in headless)
if (!window.chrome) {
    window.chrome = {
        app: {
            isInstalled: false,
            InstallState: {DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed'},
            RunningState: {CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running'}
        },
        runtime: {
            OnInstalledReason: {CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update'},
            OnRestartRequiredReason: {APP_UPDATE: 'app_update', GC_PRESSURE: 'gc_pressure', OS_UPDATE: 'os_update'},
            PlatformArch: {ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64'},
            PlatformNaclArch: {ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64'},
            PlatformOs: {ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win'},
            RequestUpdateCheckStatus: {NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available'}
        }
    };
}

// 5. Fix Permissions API (headless throws error instead of returning 'denied')
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// 6. Canvas fingerprint noise (adds micro-noise to resist fingerprinting)
const getImageDataOriginal = CanvasRenderingContext2D.prototype.getImageData;
CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
    const imageData = getImageDataOriginal.call(this, x, y, w, h);
    for (let i = 0; i < imageData.data.length; i += 100) {
        imageData.data[i] = imageData.data[i] ^ 1;
    }
    return imageData;
};

// 7. WebGL renderer string randomization
const getParameterOriginal = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    // UNMASKED_VENDOR_WEBGL
    if (parameter === 37445) return 'Intel Inc.';
    // UNMASKED_RENDERER_WEBGL
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameterOriginal.call(this, parameter);
};

// 8. Media devices (headless returns empty)
Object.defineProperty(navigator, 'mediaDevices', {
    get: () => ({
        enumerateDevices: () => Promise.resolve([
            {kind: 'audioinput', deviceId: 'default', label: '', groupId: 'default'},
            {kind: 'audiooutput', deviceId: 'default', label: '', groupId: 'default'},
            {kind: 'videoinput', deviceId: 'abc123', label: '', groupId: 'xyz789'}
        ])
    }),
    configurable: true
});
"""


def get_stealth_script() -> str:
    return STEALTH_SCRIPT


def get_random_viewport() -> dict:
    """Return a random realistic viewport size."""
    widths = [1280, 1366, 1440, 1536, 1920]
    heights = [720, 768, 800, 864, 900, 1080]
    return {
        "width": random.choice(widths),
        "height": random.choice(heights),
    }
