/** Photo rules shared with the backend: JPEG, PNG or WebP up to 5 MB. */
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const MAX_PHOTO_MB = 5

/** Returns an error message for an unsuitable file, or null when it can be uploaded. */
export const validatePhoto = (file) => {
    if (!PHOTO_TYPES.includes(file.type)) return 'Фото должно быть в формате JPEG, PNG или WebP'
    if (file.size > MAX_PHOTO_MB * 1024 * 1024) return `Фото должно быть не больше ${MAX_PHOTO_MB} МБ`
    return null
}
