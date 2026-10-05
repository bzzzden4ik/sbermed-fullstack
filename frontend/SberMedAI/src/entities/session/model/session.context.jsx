import { useState, useEffect, useCallback, useMemo } from 'react';
import { tokenStorage, AUTH_EXPIRED_EVENT } from '@/shared/api/axios-client.js';
import { acceptTermsRequest, fetchMe, fetchRoleProfile, loginRequest, registerRequest } from '../api/session-api.js';
import { SessionContext } from './session-context.js';

export const SessionProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(() => !!tokenStorage.get());

  const loadSession = useCallback(async () => {
    const me = await fetchMe();
    const roleProfile = await fetchRoleProfile(me);
    setUser(me);
    setProfile(roleProfile);
    return me;
  }, []);

  useEffect(() => {
    if (tokenStorage.get()) {
      fetchMe()
        .then(async (me) => {
          const roleProfile = await fetchRoleProfile(me);
          setUser(me);
          setProfile(roleProfile);
        })
        .catch(() => {
          tokenStorage.clear();
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    }

    const onExpired = () => {
      setUser(null);
      setProfile(null);
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  const login = useCallback(async (email, password) => {
    const { access_token } = await loginRequest(email, password);
    tokenStorage.set(access_token);
    try {
      return await loadSession();
    } catch (error) {
      tokenStorage.clear();
      throw error;
    }
  }, [loadSession]);

  const register = useCallback(async (email, password, fullName) => {
    await registerRequest(email, password, fullName);
    return login(email, password);
  }, [login]);

  const acceptTerms = useCallback(async () => {
    const updated = await acceptTermsRequest();
    const roleProfile = await fetchRoleProfile(updated);
    setUser(updated);
    setProfile(roleProfile);
    return updated;
  }, []);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
    setProfile(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!user) return null;
    const roleProfile = await fetchRoleProfile(user);
    setProfile(roleProfile);
    return roleProfile;
  }, [user]);

  const value = useMemo(() => ({
    user,
    profile,
    role: user?.role || null,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshProfile,
    setProfile,
    acceptTerms,
  }), [user, profile, isLoading, login, register, logout, refreshProfile, acceptTerms]);

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
};
