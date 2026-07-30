import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, FolderOpen, Sparkles, Activity, Wand2 } from 'lucide-react';
import logoImage from '../assets/images/logo.png';

const navigation = [
  { name: 'Search', href: '/search', icon: Search },
  { name: 'Library', href: '/directories', icon: FolderOpen },
  { name: 'Generate', href: '/generate', icon: Wand2 },
  { name: 'Generators', href: '/generators', icon: Sparkles },
  { name: 'Status', href: '/status', icon: Activity },
];

const Layout = ({ children }) => {
  return (
    <div className="h-screen flex bg-ink-50 overflow-hidden">
      {/* Navigation rail */}
      <aside className="w-[248px] shrink-0 bg-ink-900 text-ink-300 flex flex-col">
        <div className="flex items-center gap-3 px-5 h-16 border-b border-white/5">
          <img src={logoImage} alt="Needle" className="h-8 w-8 object-contain" />
          <div className="leading-tight">
            <div className="text-white font-semibold tracking-tight">Needle</div>
            <div className="text-[11px] text-ink-500">Image search</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `nav-item ${
                    isActive
                      ? 'bg-white/10 text-white shadow-inner'
                      : 'text-ink-400 hover:text-white hover:bg-white/5'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`h-[18px] w-[18px] ${isActive ? 'text-needle-400' : ''}`} />
                    {item.name}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="px-5 py-4 border-t border-white/5 text-[11px] text-ink-600">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Running locally
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {children}
      </main>
    </div>
  );
};

export default Layout;
