import { useState } from 'react'
import { useSession } from '@/entities/session'
import { uploadPatientPhoto, deletePatientPhoto } from '@/entities/patient/api/patient-api.js'
import { usePatientPhoto } from '@/entities/patient/model/use-patient-photo.js'
import { getErrorMessage } from '@/shared/api/axios-client.js'
import { useToast } from '@/shared/ui/toast-context.js'
import { initials } from '@/shared/lib/format.js'
import { PHOTO_TYPES, validatePhoto } from '@/shared/lib/photo.js'

/** The patient's avatar in the cabinet: click to upload or replace the photo, link to remove it. */
export const PatientPhotoEditor = () => {
    const { profile, setProfile } = useSession()
    const toast = useToast()
    const [version, setVersion] = useState(0)
    const [busy, setBusy] = useState(false)
    const photo = usePatientPhoto(profile.id, profile.has_photo, version)

    const choose = async (e) => {
        const file = e.target.files?.[0]
        e.target.value = ''
        if (!file || busy) return
        const problem = validatePhoto(file)
        if (problem) { toast.error(problem); return }
        setBusy(true)
        try {
            setProfile(await uploadPatientPhoto(profile.id, file))
            setVersion((v) => v + 1)
            toast.show('Фото обновлено')
        } catch (err) {
            toast.error(getErrorMessage(err))
        } finally {
            setBusy(false)
        }
    }

    const remove = async () => {
        if (busy || !window.confirm('Удалить фото профиля?')) return
        setBusy(true)
        try {
            setProfile(await deletePatientPhoto(profile.id))
            toast.show('Фото удалено')
        } catch (err) {
            toast.error(getErrorMessage(err))
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="ava-wrap">
            <label className={`ava ava-edit${busy ? ' busy' : ''}`} title="Изменить фото">
                {photo ? <img src={photo} alt="Ваше фото" /> : <span aria-hidden="true">{initials(profile.full_name)}</span>}
                <span className="ava-cam">{busy ? 'Загрузка…' : profile.has_photo ? 'Изменить фото' : 'Добавить фото'}</span>
                <input type="file" className="sr-only" accept={PHOTO_TYPES.join(',')} onChange={choose} disabled={busy}
                    aria-label={profile.has_photo ? 'Изменить фото профиля' : 'Добавить фото профиля'} />
            </label>
            {profile.has_photo && <button type="button" className="alink ava-del" onClick={remove} disabled={busy}>Удалить фото</button>}
        </div>
    )
}
