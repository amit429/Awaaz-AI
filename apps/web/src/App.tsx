import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { setAppLanguage } from './i18n';
import { Button } from '@/components/ui/button';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Centered } from '@/components/AppShell';
import { Skeleton } from '@/components/ui/skeleton';
import { Login } from './features/auth/Login';
import { Consent } from './features/consent/Consent';
import { Call } from './features/call/Call';
import { Contacts } from './features/contacts/Contacts';
import { CallDetail } from './features/history/CallDetail';
import { CallLog } from './features/history/CallLog';
import { Home } from './features/home/Home';
import { Onboarding } from './features/onboarding/Onboarding';
import { Me } from './features/profile/Me';
import { Phrases } from './features/profile/Phrases';
import { useMe } from './hooks/useData';
import { useSession } from './hooks/useSession';

/** Everything except onboarding needs a saved profile (the name is spoken at the start of each call). */
function Gate() {
  const { t } = useTranslation();
  const me = useMe();
  useEffect(() => {
    if (me.data?.onboarded) void setAppLanguage(me.data.profile.app_lang);
  }, [me.data?.onboarded, me.data?.profile.app_lang]);
  useEffect(() => {
    document.documentElement.classList.toggle('large-text', Boolean(me.data?.profile.easy_font));
  }, [me.data?.profile.easy_font]);

  if (me.isError) {
    return (
      <Centered>
        <p role="alert" className="text-center">{t('common.serverDown')}</p>
        <Button className="mx-auto mt-4" onClick={() => void me.refetch()}>{t('common.tryAgain')}</Button>
      </Centered>
    );
  }
  if (!me.data) return <Centered><Skeleton className="h-8 w-40" /><Skeleton className="mt-6 h-40 w-full" /></Centered>;
  if (!me.data.consented) return <Navigate to="/consent" replace />;
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
      <Route path="/consent" element={<Consent />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<Gate />}>
        <Route path="/" element={<Home />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/me" element={<Me />} />
        <Route path="/me/phrases" element={<Phrases />} />
        <Route path="/calls" element={<CallLog />} />
        <Route path="/calls/:id" element={<CallDetail />} />
        <Route path="/call/:sessionId" element={<Call />} />
      </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
