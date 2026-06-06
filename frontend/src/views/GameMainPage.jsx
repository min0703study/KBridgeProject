import {
  Battery,
  Bell,
  ChevronRight,
  Clock3,
  Coffee,
  Factory,
  Gamepad2,
  Hotel,
  LayoutGrid,
  Settings,
  ShoppingBag,
  Signal,
  Star,
  Utensils,
  Waves,
  Wifi,
} from 'lucide-react';
import { getMockGameData } from '../mock/mockGameData.js';

const MOCK_FILTER_ICONS = {
  retail: ShoppingBag,
  dining: Utensils,
  hospitality: Bell,
  resort: Waves,
  manufacturing: Settings,
  beginner: Star,
};

function MockPhoneStatusBar() {
  return (
    <div className="phone-status-bar" aria-label="Mock phone status bar">
      <span className="phone-time">9:41</span>
      <div className="phone-island" aria-hidden="true">
        <span />
      </div>
      <div className="phone-indicators" aria-hidden="true">
        <Signal size={18} strokeWidth={3} />
        <Wifi size={18} strokeWidth={3} />
        <Battery size={22} strokeWidth={2.5} />
      </div>
    </div>
  );
}

function MockGameHeader({ profileInitial }) {
  return (
    <header className="dashboard-header game-header">
      <img
        className="yici-logo"
        src="/01_yici_logo_lockup.png"
        alt="Yale International Cultural Institute"
      />
      <div className="header-actions">
        <div className="language-toggle" aria-label="Mock language toggle">
          <button className="language-option is-active" type="button">
            EN
          </button>
          <button className="language-option" type="button">
            KR
          </button>
        </div>
        <button className="profile-button" type="button" aria-label="Mock profile">
          {profileInitial}
        </button>
      </div>
    </header>
  );
}

function MockFilterIcon({ icon }) {
  const Icon = MOCK_FILTER_ICONS[icon];

  if (!Icon) {
    return null;
  }

  return <Icon size={15} strokeWidth={1.9} aria-hidden="true" />;
}

function MockGameFilters({ filters }) {
  return (
    <div className="game-filter-strip" aria-label="Mock roleplay filters">
      {filters.map((filter) => (
        <button className={`game-filter-chip ${filter.active ? 'is-active' : ''}`} type="button" key={filter.id}>
          <MockFilterIcon icon={filter.icon} />
          <span>{filter.label}</span>
        </button>
      ))}
    </div>
  );
}

function MockRoleplayCard({ game }) {
  const categoryIcon = {
    'Convenience Store': ShoppingBag,
    Restaurant: Utensils,
    Hotel,
    Resort: Waves,
    'Factory Visit': Factory,
    Cafe: Coffee,
  }[game.title];
  const CategoryIcon = categoryIcon || Gamepad2;

  return (
    <article className="roleplay-card">
      <img className="roleplay-image" src={game.imageSrc} alt={game.imageAlt} />
      <div className="roleplay-body">
        <div>
          <h2>{game.title}</h2>
          <p>{game.description}</p>
        </div>
        <div className="roleplay-meta-row">
          <span className={`difficulty-pill tone-${game.difficultyTone}`}>{game.difficulty}</span>
          <span className="duration-meta">
            <Clock3 size={15} strokeWidth={2} aria-hidden="true" />
            {game.duration}
          </span>
        </div>
        <button className="roleplay-start-button" type="button" aria-label={`Start ${game.title} mock roleplay`}>
          <CategoryIcon className="roleplay-start-icon" size={18} strokeWidth={2} aria-hidden="true" />
          <ChevronRight size={23} strokeWidth={2.8} aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}

function MockGameBottomNavigation({ items, onMockNavigate }) {
  return (
    <nav className="bottom-nav" aria-label="Mock app navigation">
      {items.map((item) => (
        <button
          className={`nav-item ${item.active ? 'is-active' : ''}`}
          type="button"
          key={item.id}
          onClick={() => {
            if (item.tab === 'dashboard' || item.tab === 'game') {
              onMockNavigate(item.tab);
            }
          }}
        >
          {item.iconSrc ? (
            <img src={item.iconSrc} alt={item.iconAlt} />
          ) : item.lucide === 'game' ? (
            <Gamepad2 size={30} strokeWidth={1.9} aria-hidden="true" />
          ) : (
            <LayoutGrid size={30} strokeWidth={1.9} aria-hidden="true" />
          )}
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

export default function GameMainPage({ onMockNavigate }) {
  const mockGameData = getMockGameData();

  return (
    <main className="app-stage">
      <div className="mobile-shell game-page-shell">
        <MockPhoneStatusBar />
        <MockGameHeader profileInitial={mockGameData.profileInitial} />
        <div className="game-scroll">
          <MockGameFilters filters={mockGameData.filters} />
          <section className="roleplay-grid" aria-label="Mock roleplay game list">
            {mockGameData.roleplayGames.map((game) => (
              <MockRoleplayCard game={game} key={game.id} />
            ))}
          </section>
        </div>
        <MockGameBottomNavigation
          items={mockGameData.bottomNavItems}
          onMockNavigate={onMockNavigate}
        />
      </div>
    </main>
  );
}
