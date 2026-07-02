import { Gamepad2, LayoutGrid } from 'lucide-react';

const NAV_ITEMS = [
  {
    id: 'nav-homework',
    tab: 'homework',
    label: 'Homework',
    iconSrc: '/08_nav_homework_note.png',
    iconAlt: 'Homework',
  },
  {
    id: 'nav-vocabulary',
    tab: 'vocabulary',
    label: 'Vocabulary',
    iconSrc: '/09_nav_vocabulary_book_aa.png',
    iconAlt: 'Vocabulary',
    disabled: true,
  },
  {
    id: 'nav-dashboard',
    tab: 'dashboard',
    label: 'Dashboard',
    icon: 'dashboard',
  },
  {
    id: 'nav-game',
    tab: 'game',
    label: 'Game',
    icon: 'game',
  },
  {
    id: 'nav-settings',
    tab: 'settings',
    label: 'Settings',
    iconSrc: '/10_nav_settings_gear.png',
    iconAlt: 'Settings',
    disabled: true,
  },
];

function NavIcon({ item }) {
  if (item.iconSrc) {
    return <img src={item.iconSrc} alt={item.iconAlt} />;
  }

  if (item.icon === 'game') {
    return <Gamepad2 size={30} strokeWidth={1.9} aria-hidden="true" />;
  }

  return <LayoutGrid size={30} strokeWidth={1.9} aria-hidden="true" />;
}

export default function AppBottomNavigation({ activeTab, onNavigate }) {
  return (
    <nav className="bottom-nav" aria-label="App navigation">
      {NAV_ITEMS.map((item) => (
        <button
          className={`nav-item ${item.tab === activeTab ? 'is-active' : ''}`}
          type="button"
          key={item.id}
          aria-current={item.tab === activeTab ? 'page' : undefined}
          aria-disabled={item.disabled ? 'true' : undefined}
          onClick={() => {
            if (!item.disabled) {
              onNavigate(item.tab);
            }
          }}
        >
          <NavIcon item={item} />
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
