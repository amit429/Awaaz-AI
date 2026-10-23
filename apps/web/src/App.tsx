import { Navigate, Route, Routes } from 'react-router-dom';
import { Call } from './features/call/Call';
import { Home } from './features/home/Home';

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/call/:sessionId" element={<Call />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
