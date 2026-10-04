import { createContext, useContext } from 'react';

export const SessionContext = createContext(null);

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession должен использоваться внутри SessionProvider');
  }
  return context;
};

/** Home page of each role's interface. */
export const homePathFor = (role) => ({ patient: '/profile', doctor: '/doctor', admin: '/admin' }[role] || '/');
