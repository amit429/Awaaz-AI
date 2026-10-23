import { useEffect } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Call } from './features/call/Call';
import { Contacts } from './features/contacts/Contacts';
import { CallDetail } from './features/history/CallDetail';
import { Home } from './features/home/Home';
import { Onboarding } from './features/onboarding/Onboarding';
import { Me } from './features/profile/Me';
import { Phrases } from './features/profile/Phrases';
import { useMe } from './hooks/useData';

/** Everything except onboarding needs a saved profile (the name is spoken at the start of each call). */
function Gate() {
  const me = useMe();
  useEffect(() => {
    document.documentElement.classList.toggle('readable', Boolean(me.data?.profile.easy_font));
  }, [me.data?.profile.easy_font]);

  if (me.isError) return <div className="app"><div className="scroll"><p className="err" role="alert">Could not reach Awaaz. Is the server running?</p><button className="cta" type="button" onClick={() => void me.refetch()}>Try again</button></div></div>;
  if (!me.data) return <div className="app"><div className="scroll"><p>Loading…</p></div></div>;
  if (!me.data.onboarded) return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

export function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<Gate />}>
        <Route path="/" element={<Home />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/me" element={<Me />} />
        <Route path="/me/phrases" element={<Phrases />} />
        <Route path="/calls/:id" element={<CallDetail />} />
        <Route path="/call/:sessionId" element={<Call />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
