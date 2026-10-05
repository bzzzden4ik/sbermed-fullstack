import { useCallback, useEffect, useRef, useState } from 'react'
import { useSession } from '@/entities/session'
import { listDoctors, createDoctor, updateDoctor, deleteDoctor, uploadDoctorPhoto, deleteDoctorPhoto } from '@/entities/doctor/api/doctor-api.js'
import { listPatients, deletePatient } from '@/entities/patient/api/patient-api.js'
import { listAppointments, updateAppointment } from '@/entities/appointment/api/appointment-api.js'
import { listCases, CaseSummary } from '@/entities/case'
import { getDashboardReport, getDoctorsReport } from '@/entities/report/api/report-api.js'
import { SiteHeader } from '@/widgets/site-header'
import { Loader, Modal, SiteFooter, StatusChip } from '@/shared/ui/common.jsx'
import { OrbitBackground, PlusIcon } from '@/shared/ui/icons.jsx'
import { useToast } from '@/shared/ui/toast-context.js'
import { getErrorMessage, mediaUrl } from '@/shared/api/axios-client.js'
import { APPOINTMENT_STATUS, CASE_DECISION, CASE_STATUS, URGENCY } from '@/shared/lib/labels.js'
import { formatDate, formatDateTime, formatGender, initials } from '@/shared/lib/format.js'
import { MAX_PHOTO_MB, PHOTO_TYPES, validatePhoto } from '@/shared/lib/photo.js'
import '../../profile/ui/cabinet.css'
import './admin.css'

const TABS = [['overview', 'Обзор'], ['doctors', 'Врачи'], ['patients', 'Пациенты'], ['appointments', 'Записи'], ['cases', 'Обращения']]

/** Loads data for a tab once; `reload` re-fetches after a mutation. */
const useResource = (loader) => {
    const toast = useToast()
    const [data, setData] = useState(null)
    const reload = useCallback(() => loader().then(setData).catch((err) => { setData([]); toast.error(getErrorMessage(err)) }), [loader, toast])
    useEffect(() => { reload() }, [reload])
    return [data, reload, setData]
}

const Table = ({ head, children }) => (
    <div className="tbl-wrap"><table className="tbl"><thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead><tbody>{children}</tbody></table></div>
)

const Overview = () => {
    const [report] = useResource(getDashboardReport)
    const [doctorsReport] = useResource(getDoctorsReport)
    const [cases] = useResource(listCases)
    if (!report || !doctorsReport || !cases) return <Loader />
    const waiting = cases.filter((c) => ['READY_FOR_DOCTOR', 'REFERRED', 'UNDER_REVIEW'].includes(c.status)).length
    return (
        <>
            <div className="stats">
                <div><div className="l">Пациентов</div><b>{report.total_patients}</b></div>
                <div><div className="l">Врачей</div><b>{report.total_doctors}</b></div>
                <div><div className="l">Записей сегодня</div><b>{report.today_appointments}</b></div>
                <div><div className="l">Обращений ждут врача</div><b>{waiting}</b></div>
            </div>
            <div className="pr" style={{ marginTop: 48 }}>
                <div>Предстоящие записи<b>{report.upcoming_appointments}</b></div>
                <div>Завершённые приёмы<b>{report.completed_appointments}</b></div>
                <div>Отменённые записи<b>{report.cancelled_appointments}</b></div>
                <div>Среднее записей в день<b>{report.average_daily_appointments}</b></div>
                <div>Самый востребованный врач<b>{report.most_visited_doctor || '—'}</b></div>
                <div>Обращений всего<b>{cases.length}</b></div>
            </div>
            <h3 style={{ margin: '48px 0 16px' }}>Нагрузка по записям</h3>
            <Table head={['Врач', 'Записей']}>
                {doctorsReport.doctors.map((d) => <tr key={d.doctor_id}><td>{d.doctor_name}</td><td>{d.appointment_count}</td></tr>)}
            </Table>
        </>
    )
}

const EMPTY_DOCTOR = { full_name: '', specialization: '', qualification: '', phone_number: '', email: '', consultation_fee: '', available_timings: 'Mon-Fri 09:00-17:00' }


const DoctorAvatar = ({ doctor, src, size = 44 }) => {
    const url = src === undefined ? mediaUrl(doctor?.photo_url) : src
    return (
        <span className="doc-ava" style={{ width: size, height: size, fontSize: size * .38 }}>
            {url ? <img src={url} alt={doctor?.full_name ? `Фото: ${doctor.full_name}` : 'Фото врача'} /> : initials(doctor?.full_name || '')}
        </span>
    )
}

const DoctorForm = ({ initial, onSaved }) => {
    const [form, setForm] = useState(initial || EMPTY_DOCTOR)
    const [photoFile, setPhotoFile] = useState(null)
    const [preview, setPreview] = useState(null)
    const [removePhoto, setRemovePhoto] = useState(false)
    const [error, setError] = useState('')
    const [pending, setPending] = useState(false)

    // Local preview of the chosen file; the object URL is released when replaced or when the form closes.
    const previewRef = useRef(null)
    const setPreviewUrl = (url) => {
        if (previewRef.current) URL.revokeObjectURL(previewRef.current)
        previewRef.current = url
        setPreview(url)
    }
    useEffect(() => () => {
        if (previewRef.current) URL.revokeObjectURL(previewRef.current)
    }, [])

    const field = (name, props = {}) => ({
        id: `df-${name}`, className: 'input', required: true, value: form[name], ...props,
        onChange: (e) => setForm((f) => ({ ...f, [name]: e.target.value })),
    })

    const choosePhoto = (e) => {
        const file = e.target.files?.[0]
        e.target.value = ''
        if (!file) return
        const problem = validatePhoto(file)
        if (problem) { setError(problem); return }
        setError('')
        setRemovePhoto(false)
        setPhotoFile(file)
        setPreviewUrl(URL.createObjectURL(file))
    }

    const clearPhoto = () => {
        setPhotoFile(null)
        setPreviewUrl(null)
        setRemovePhoto(!!initial?.photo_url)
    }

    const submit = async (e) => {
        e.preventDefault()
        setPending(true)
        setError('')
        try {
            const payload = { ...form, consultation_fee: Number(form.consultation_fee) }
            let saved = initial ? await updateDoctor(initial.id, payload) : await createDoctor(payload)
            if (photoFile) saved = await uploadDoctorPhoto(saved.id, photoFile)
            else if (removePhoto) saved = await deleteDoctorPhoto(saved.id)
            onSaved(saved)
        } catch (err) {
            setError(getErrorMessage(err))
            setPending(false)
        }
    }

    const shownPhoto = photoFile ? preview : removePhoto ? null : mediaUrl(initial?.photo_url)

    return (
        <form onSubmit={submit}>
            {error && <div className="form-error">{error}</div>}
            <div className="photo-field">
                <DoctorAvatar doctor={form} src={shownPhoto} size={88} />
                <div>
                    <div className="lbl">Фотография</div>
                    <p className="muted">JPEG, PNG или WebP, до {MAX_PHOTO_MB} МБ. Видна пациентам на сайте.</p>
                    <div className="photo-acts">
                        <label className="btn sm ghost">
                            {shownPhoto ? 'Заменить фото' : 'Загрузить фото'}
                            <input type="file" accept={PHOTO_TYPES.join(',')} onChange={choosePhoto} className="sr-only" />
                        </label>
                        {shownPhoto && <button type="button" className="alink" onClick={clearPhoto}>Удалить фото</button>}
                    </div>
                </div>
            </div>
            <div className="fg"><label htmlFor="df-full_name">ФИО</label><input {...field('full_name', { minLength: 2 })} /></div>
            <div className="grid2">
                <div className="fg"><label htmlFor="df-specialization">Специализация</label><input {...field('specialization', { minLength: 2, placeholder: 'Cardiology' })} /></div>
                <div className="fg"><label htmlFor="df-qualification">Квалификация</label><input {...field('qualification', { minLength: 2 })} /></div>
                <div className="fg"><label htmlFor="df-email">Email</label><input {...field('email', { type: 'email', disabled: !!initial })} /></div>
                <div className="fg"><label htmlFor="df-phone_number">Телефон</label><input {...field('phone_number', { minLength: 5 })} /></div>
                <div className="fg"><label htmlFor="df-consultation_fee">Стоимость приёма, ₽</label><input {...field('consultation_fee', { type: 'number', min: 1 })} /></div>
                <div className="fg"><label htmlFor="df-available_timings">Часы приёма</label><input {...field('available_timings', { minLength: 5 })} /></div>
            </div>
            {!initial && <p className="muted" style={{ fontSize: 13, marginBottom: 14 }}>Если учётной записи с этим email нет, она будет создана с паролем по умолчанию <b>doctor123</b>.</p>}
            <button className="btn" type="submit" disabled={pending} style={{ width: '100%' }}>{pending ? 'Сохраняем…' : 'Сохранить'}</button>
        </form>
    )
}

const Doctors = () => {
    const toast = useToast()
    const [doctors, reload] = useResource(useCallback(() => listDoctors({ limit: 1000 }), []))
    const [editing, setEditing] = useState(null)
    const remove = async (d) => {
        if (!window.confirm(`Удалить врача ${d.full_name}?`)) return
        try { await deleteDoctor(d.id); toast.show('Врач удалён'); reload() } catch (err) { toast.error(getErrorMessage(err)) }
    }
    if (!doctors) return <Loader />
    return (
        <>
            <div className="tbl-actions"><button className="btn sm" onClick={() => setEditing({})}><PlusIcon />Добавить врача</button></div>
            <Table head={['', 'ФИО', 'Специализация', 'Email', 'Часы приёма', 'Аккаунт', '']}>
                {doctors.map((d) => (
                    <tr key={d.id}>
                        <td style={{ width: 60 }}><DoctorAvatar doctor={d} /></td>
                        <td><b>{d.full_name}</b><small>{d.qualification}</small></td>
                        <td>{d.specialization}</td>
                        <td>{d.email}</td>
                        <td>{d.available_timings}</td>
                        <td>{d.user_id ? <span className="st ok">есть</span> : <span className="st bad">нет</span>}</td>
                        <td className="row-acts">
                            <button className="alink" onClick={() => setEditing(d)}>Изменить</button>
                            <button className="alink" onClick={() => remove(d)}>Удалить</button>
                        </td>
                    </tr>
                ))}
            </Table>
            {editing && (
                <Modal title={editing.id ? 'Врач' : 'Новый врач'} width={620} onClose={() => setEditing(null)}>
                    <DoctorForm initial={editing.id ? editing : null} onSaved={() => { setEditing(null); toast.show('Сохранено'); reload() }} />
                </Modal>
            )}
        </>
    )
}

const Patients = () => {
    const toast = useToast()
    const [patients, reload] = useResource(useCallback(() => listPatients({ limit: 1000 }), []))
    const remove = async (p) => {
        if (!window.confirm(`Удалить пациента ${p.full_name} вместе с его записями и обращениями?`)) return
        try { await deletePatient(p.id); toast.show('Пациент удалён'); reload() } catch (err) { toast.error(getErrorMessage(err)) }
    }
    if (!patients) return <Loader />
    return (
        <Table head={['ФИО', 'Возраст', 'Пол', 'Телефон', 'Группа крови', 'Создан', '']}>
            {patients.map((p) => (
                <tr key={p.id}>
                    <td><b>{p.full_name}</b><small>{p.address}</small></td>
                    <td>{p.age}</td>
                    <td>{formatGender(p.gender)}</td>
                    <td>{p.phone_number}</td>
                    <td>{p.blood_group}</td>
                    <td>{formatDate(p.created_at)}</td>
                    <td className="row-acts"><button className="alink" onClick={() => remove(p)}>Удалить</button></td>
                </tr>
            ))}
        </Table>
    )
}

const Appointments = () => {
    const toast = useToast()
    const [items, , setItems] = useResource(useCallback(() => listAppointments({ sort_by: 'appointment_date', order: 'desc', limit: 500 }), []))
    const changeStatus = async (a, status) => {
        try {
            const updated = await updateAppointment(a.id, { status })
            setItems((list) => list.map((x) => (x.id === updated.id ? updated : x)))
            toast.show('Статус обновлён')
        } catch (err) { toast.error(getErrorMessage(err)) }
    }
    if (!items) return <Loader />
    return (
        <Table head={['Номер', 'Дата', 'Пациент', 'Врач', 'Причина', 'Статус']}>
            {items.map((a) => (
                <tr key={a.id}>
                    <td><small style={{ fontFamily: 'monospace' }}>{a.appointment_number}</small></td>
                    <td>{formatDate(a.appointment_date)}<small>{a.time_slot}</small></td>
                    <td>{a.patient.full_name}</td>
                    <td>{a.doctor.full_name}<small>{a.doctor.specialization}</small></td>
                    <td>{a.reason_for_visit}</td>
                    <td>
                        <select className="input sm" value={a.status} onChange={(e) => changeStatus(a, e.target.value)} aria-label="Статус записи">
                            {Object.entries(APPOINTMENT_STATUS).map(([value, { label }]) => <option key={value} value={value}>{label}</option>)}
                        </select>
                    </td>
                </tr>
            ))}
        </Table>
    )
}

const Cases = () => {
    const [cases] = useResource(listCases)
    const [open, setOpen] = useState(null)
    if (!cases) return <Loader />
    return (
        <>
            <Table head={['№', 'Пациент', 'Жалоба', 'Врач', 'Статус', 'Обновлено']}>
                {cases.map((c) => (
                    <tr key={c.id} className="clickable" onClick={() => setOpen(c)}>
                        <td>{c.id}</td>
                        <td>{c.patient.full_name}</td>
                        <td>{c.complaint}</td>
                        <td>{c.doctor ? <>{c.doctor.full_name}<small>{c.doctor.specialization}</small></> : '—'}</td>
                        <td><StatusChip map={CASE_STATUS} value={c.status} /></td>
                        <td>{formatDateTime(c.updated_at)}</td>
                    </tr>
                ))}
            </Table>
            {open && (
                <Modal title={`Обращение №${open.id}`} width={760} onClose={() => setOpen(null)}>
                    <div className="sub" style={{ margin: '0 0 18px' }}>
                        <StatusChip map={CASE_STATUS} value={open.status} />
                        <StatusChip map={URGENCY} value={open.urgency} />
                        {open.decision && <StatusChip map={CASE_DECISION} value={open.decision} />}
                    </div>
                    <CaseSummary summary={open.ai_summary} />
                    {open.doctor_comment && <p style={{ marginTop: 16 }}><b>Комментарий врача:</b> {open.doctor_comment}</p>}
                </Modal>
            )}
        </>
    )
}

export function AdminPage() {
    const { user } = useSession()
    const [tab, setTab] = useState('overview')
    const Panel = { overview: Overview, doctors: Doctors, patients: Patients, appointments: Appointments, cases: Cases }[tab]

    return (
        <div className="page p-cabinet p-admin">
            <SiteHeader />
            <main>
                <div className="hero">
                    <OrbitBackground />
                    <div className="wrap">
                        <div className="crumbs"><span>Администрирование</span><span>/</span><b>{TABS.find(([v]) => v === tab)[1]}</b></div>
                        <h1>Панель <i>клиники</i></h1>
                        <div className="sub"><span className="chip">Администратор</span><span>{user.full_name}</span><span>{user.email}</span></div>
                        <div className="tabs" role="tablist">
                            {TABS.map(([value, label]) => (
                                <button key={value} role="tab" aria-selected={tab === value} className={tab === value ? 'on' : ''} onClick={() => setTab(value)}>{label}</button>
                            ))}
                        </div>
                    </div>
                </div>
                <section className="s">
                    <div className="wrap"><Panel /></div>
                </section>
            </main>
            <SiteFooter />
        </div>
    )
}
