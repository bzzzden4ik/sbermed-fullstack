import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSession, homePathFor } from '@/entities/session';
import { Loader } from '@/shared/ui/common.jsx';

const FullPageLoader = () => <div style={{ flex: 1, display: 'grid', placeItems: 'center' }}><Loader /></div>;

/**
 * Only lets users with one of `roles` through. UI guard only — the backend enforces every permission again.
 * Patients first accept the legal documents (consent screen), then create a profile (onboarding).
 */
export const RoleRoute = ({ roles, allowMissingProfile = false, allowMissingConsent = false }) => {
  const { isAuthenticated, isLoading, role, profile, user } = useSession();
  const location = useLocation();

  if (isLoading) return <FullPageLoader />;
  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location.pathname + location.search + location.hash }} />;
  }
  if (!roles.includes(role)) return <Navigate to={homePathFor(role)} replace />;
  if (role === 'patient' && user.needs_consent && !allowMissingConsent) {
    return <Navigate to="/consent" replace state={{ from: location.pathname + location.search + location.hash }} />;
  }
  if (role === 'patient' && !profile && !allowMissingProfile) {
    return <Navigate to="/onboarding" replace state={{ from: location.pathname + location.search + location.hash }} />;
  }
  return <Outlet />;
};

export const PublicOnlyRoute = () => {
  const { isAuthenticated, isLoading, role } = useSession();
  const location = useLocation();

  if (isLoading) return <FullPageLoader />;
  return !isAuthenticated ? <Outlet /> : <Navigate to={location.state?.from || homePathFor(role)} replace />;
};

export const CabinetRedirect = () => {
  const { isAuthenticated, isLoading, role } = useSession();
  if (isLoading) return <FullPageLoader />;
  return <Navigate to={isAuthenticated ? homePathFor(role) : '/auth'} replace />;
};
