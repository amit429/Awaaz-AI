import { NavLink } from 'react-router-dom';
import { Icon, type IconName } from './Icons';

const TABS: { to: string; icon: IconName; label: string; end?: boolean }[] = [
  { to: '/', icon: 'phone', label: 'Calls', end: true },
  { to: '/contacts', icon: 'people', label: 'Contacts' },
  { to: '/me', icon: 'user', label: 'Me' },
];

export function TabBar() {
  return (
    <nav className="tabbar" aria-label="Main">
      {TABS.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.end} style={{ textDecoration: 'none', color: 'inherit' }}>
          {({ isActive }) => (
            <span className={isActive ? 'on' : ''}>
              <Icon name={t.icon} />
              {t.label}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
