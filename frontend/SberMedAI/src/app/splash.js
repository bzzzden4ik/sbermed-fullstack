// Fades out the splash screen from index.html once the app is ready.
// It stays at least MIN_VISIBLE_MS so a fast load does not flicker; index.html hides it after 8 s regardless.
const MIN_VISIBLE_MS = 800
const FONT_WAIT_MS = 1500

let hiding = false

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export const hideSplash = async () => {
    const el = document.getElementById('splash')
    if (hiding || !el) return
    hiding = true

    // Avoid a visible font swap right after the splash disappears, without waiting forever for slow fonts.
    try {
        await Promise.race([document.fonts?.ready, wait(FONT_WAIT_MS)])
    } catch {
        // fonts API unavailable: continue
    }

    const shownFor = performance.now() - (window.__splashStart || 0)
    await wait(Math.max(0, MIN_VISIBLE_MS - shownFor))

    el.classList.add('sp-hide')
    el.addEventListener('transitionend', () => el.remove(), { once: true })
    setTimeout(() => el.remove(), 700) // in case transitionend does not fire (e.g. reduced motion)
}
