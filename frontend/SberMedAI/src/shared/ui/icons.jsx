/* Line icons copied from the SIRIUS templates. */

export const HeartLogoIcon = () => (
    <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 21.5s-8.5-5.4-8.5-11.6A4.8 4.8 0 0 1 12 7a4.8 4.8 0 0 1 8.5 2.9c0 6.2-8.5 11.6-8.5 11.6z" fill="#fff" />
        <path d="M5.5 12.5h3.2l1.6-3.2 2.6 6 1.8-2.8h3.8" fill="none" stroke="#0F5B68" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
)

export const SparkIcon = ({ size = 14, color = '#fff' }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden="true">
        <path d="M12 0c.8 7.2 4.8 11.2 12 12-7.2.8-11.2 4.8-12 12-.8-7.2-4.8-11.2-12-12C7.2 11.2 11.2 7.2 12 0z" />
    </svg>
)

export const ArrowRightIcon = ({ size = 16 }) => (
    <svg className="arrow" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M5 12h14m-6-6 6 6-6 6" />
    </svg>
)

export const ArrowUpRightIcon = ({ size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M7 17 17 7M8 7h9v9" />
    </svg>
)

export const BellIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
        <path d="M6 17V11a6 6 0 0 1 12 0v6l1.5 2h-15zM10 21h4" />
    </svg>
)

export const UserIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
        <circle cx="12" cy="7.5" r="4" />
        <path d="M4 21v-1.5a5 5 0 0 1 5-5h6a5 5 0 0 1 5 5V21" />
    </svg>
)

export const LogoutIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
        <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10" />
    </svg>
)

export const CloseIcon = ({ size = 14 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M6 6l12 12M18 6 6 18" />
    </svg>
)

export const PlusIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <path d="M12 5v14M5 12h14" />
    </svg>
)

export const MenuIcon = () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M4 7h16M4 12h16M4 17h10" />
    </svg>
)

export const SearchIcon = ({ size = 16 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
    </svg>
)

export const MicIcon = () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
        <rect x="9" y="3" width="6" height="12" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
)

export const SendIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 19V5m-6 6 6-6 6 6" />
    </svg>
)

export const TrashIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
        <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
    </svg>
)

export const OrbitBackground = () => (
    <div className="hbg-orbit" aria-hidden="true">
        <svg viewBox="0 0 900 600" preserveAspectRatio="xMidYMid slice">
            <g className="orb">
                <circle cx="600" cy="300" r="120" fill="none" stroke="#0F5B68" strokeOpacity=".28" />
                <circle cx="600" cy="300" r="210" fill="none" stroke="#0F5B68" strokeOpacity=".2" />
                <circle cx="600" cy="300" r="310" fill="none" stroke="#0F5B68" strokeOpacity=".14" />
                <circle cx="600" cy="300" r="420" fill="none" stroke="#0F5B68" strokeOpacity=".08" />
                <circle cx="720" cy="300" r="5" fill="#0F5B68" />
                <circle cx="390" cy="300" r="4" fill="#8FD9C4" />
                <circle cx="600" cy="90" r="4" fill="#0F5B68" fillOpacity=".6" />
            </g>
        </svg>
    </div>
)
