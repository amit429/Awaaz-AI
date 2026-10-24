import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Centered } from '@/components/AppShell';
import { Skeleton } from '@/components/ui/skeleton';
import { Login } from './features/auth/Login';
import { Call } from './features/call/Call';
import { Contacts } from './features/contacts/Contacts';
import { CallDetail } from './features/history/CallDetail';
import { Home } from './features/home/Home';
import { Onboarding } from './features/onboarding/Onboarding';
import { Me } from './features/profile/Me';
import { Phrases } from './features/profile/Phrases';
import { useMe } from './hooks/useData';
import { useSession } from './hooks/useSession';

/** Everything except onboarding needs a saved profile (the name is spoken at the start of each call). */
function Gate() {
  const me = useMe();
  useEffect(() => {
    document.documentElement.classList.toggle('large-text', Boolean(me.data?.profile.easy_font));
  }, [me.data?.profile.easy_font]);

  if (me.isError) {
    return (
      <Centered>
        <p role="alert" className="text-center">Could not reach Awaaz. The server may be starting up, which can take a minute.</p>
        <Button className="mx-auto mt-4" onClick={() => void me.refetch()}>Try again</Button>
      </Centered>
    );
  }
  if (!me.data) return <Centered><Skeleton className="h-8 w-40" /><Skeleton className="mt-6 h-40 w-full" /></Centered>;
  if (!me.data.onboarded) return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

function RequireAuth() {
  const session = useSession();
  if (session.loading) return <Centered><Skeleton className="h-8 w-40" /><Skeleton className="mt-6 h-40 w-full" /></Centered>;
  return session.signedIn ? <Outlet /> : <Navigate to="/login" replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<Gate />}>
        <Route path="/" element={<Home />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/me" element={<Me />} />
        <Route path="/me/phrases" element={<Phrases />} />
        <Route path="/calls/:id" element={<CallDetail />} />
        <Route path="/call/:sessionId" element={<Call />} />
      </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
