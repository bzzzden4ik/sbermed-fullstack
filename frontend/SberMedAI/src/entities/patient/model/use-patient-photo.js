import { useEffect, useState } from 'react'
import { fetchPatientPhoto } from '../api/patient-api.js'

/**
 * Object URL of a patient's private photo (null when there is none). `version` forces a reload after a change.
 * The URL is revoked when the photo changes or the component unmounts.
 */
export const usePatientPhoto = (patientId, hasPhoto, version = 0) => {
    const [loaded, setLoaded] = useState({ key: null, url: null })
    const key = hasPhoto && patientId ? `${patientId}:${version}` : null

    useEffect(() => {
        if (!key) return undefined
        let url = null
        let cancelled = false
        fetchPatientPhoto(patientId)
            .then((blob) => {
                if (cancelled) return
                url = URL.createObjectURL(blob)
                setLoaded({ key, url })
            })
            .catch(() => { if (!cancelled) setLoaded({ key, url: null }) })
        return () => {
            cancelled = true
            if (url) URL.revokeObjectURL(url)
        }
    }, [key, patientId])

    return loaded.key === key ? loaded.url : null
}
