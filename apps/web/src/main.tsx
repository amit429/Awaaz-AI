import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { IconSprite } from './components/Icons';
import './styles/tokens.css';
import './styles/app.css';

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <IconSprite />
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
