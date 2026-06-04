import {
  Battery,
  ChevronLeft,
  ChevronRight,
  Gamepad2,
  LayoutGrid,
  Signal,
  Sun,
  Wifi,
} from 'lucide-react';
import { getMockDashboardData } from '../mock/mockDashboardData.js';

const MOCK_EVENT_LABELS = {
  class: 'Class',
  homework: 'Homework',
  completed: 'Completed',
};

function PhoneStatusBar() {
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

function Header({ profileInitial }) {
  return (
    <header className="dashboard-header">
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

function HeroCard() {
  return (
    <section className="hero-card" aria-label="Daily encouragement">
      <div className="hero-copy">
        <Sun className="hero-sun" size={32} strokeWidth={2.1} aria-hidden="true" />
        <h1>You&apos;re doing great!</h1>
        <p>Consistent practice brings confident conversations.</p>
      </div>
      <img
        className="hero-students"
        src="/02_dashboard_hero_students.png"
        alt="Students practicing conversation"
      />
    </section>
  );
}

function StatusCard({ statusItems }) {
  return (
    <section className="status-card" aria-labelledby="today-status-title">
      <h2 id="today-status-title">Today&apos;s Status</h2>
      <div className="status-grid">
        {statusItems.map((item) => (
          <article className="status-item" key={item.id}>
            <img className="status-icon" src={item.iconSrc} alt={item.iconAlt} />
            <span className="status-label">{item.label}</span>
            <strong className={`status-value tone-${item.valueTone}`}>{item.value}</strong>
            {item.unit ? <span className="status-unit">{item.unit}</span> : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function TripCard({ countdown }) {
  return (
    <section className="trip-card" aria-label="Trip to Korea countdown">
      <div className="trip-copy">
        <h2>Trip to Korea</h2>
        <strong>{countdown}</strong>
        <p>Until your Korea journey begins</p>
      </div>
      <img
        className="trip-image"
        src="/03_trip_to_korea_illustration.png"
        alt="Airplane flying over Korea landmarks"
      />
    </section>
  );
}

function CalendarSection({ currentMonth, calendarDays, upcomingSchedule }) {
  return (
    <section className="calendar-card" aria-labelledby="calendar-title">
      <div className="calendar-header">
        <h2 id="calendar-title">Calendar</h2>
        <div className="month-switcher" aria-label="Mock month controls">
          <span>{currentMonth}</span>
          <button type="button" aria-label="Previous month">
            <ChevronLeft size={20} />
          </button>
          <button type="button" aria-label="Next month">
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      <div className="weekday-grid" aria-hidden="true">
        {['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'].map((day) => (
          <span key={day}>{day}</span>
        ))}
      </div>

      <div className="calendar-grid">
        {calendarDays.map((day, index) => (
          <div
            className={`calendar-day ${day.muted ? 'is-muted' : ''} ${
              day.selected ? `is-selected selected-${day.selected}` : ''
            }`}
            key={`${day.date}-${index}`}
          >
            <span className="calendar-date">{day.date}</span>
            <span className="calendar-dots" aria-label={mockEventText(day.events)}>
              {(day.events || []).map((eventType, eventIndex) => (
                <span
                  className={`event-dot dot-${eventType}`}
                  key={`${eventType}-${eventIndex}`}
                  aria-hidden="true"
                />
              ))}
            </span>
          </div>
        ))}
      </div>

      <div className="calendar-legend">
        {Object.entries(MOCK_EVENT_LABELS).map(([type, label]) => (
          <span key={type}>
            <span className={`event-dot dot-${type}`} aria-hidden="true" />
            {label}
          </span>
        ))}
      </div>

      <div className="schedule-divider" />
      <div className="schedule-header">
        <h3>Upcoming Schedule</h3>
        <button type="button">View all</button>
      </div>
      <div className="schedule-list">
        {upcomingSchedule.map((item) => (
          <article className="schedule-row" key={item.id}>
            <span className={`event-dot dot-${item.type}`} aria-hidden="true" />
            <strong>{item.day}</strong>
            <span>{item.time}</span>
            <b>{item.title}</b>
            <ChevronRight className="schedule-arrow" size={20} aria-hidden="true" />
          </article>
        ))}
      </div>
    </section>
  );
}

function mockEventText(events = []) {
  if (!events.length) {
    return 'No mock events';
  }

  return events.map((eventType) => MOCK_EVENT_LABELS[eventType]).join(', ');
}

function BottomNavigation({ items, onMockNavigate }) {
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

export default function DashboardMainPage({ onMockNavigate }) {
  const mockDashboardData = getMockDashboardData();

  return (
    <main className="app-stage">
      <div className="mobile-shell">
        <PhoneStatusBar />
        <Header profileInitial={mockDashboardData.profileInitial} />
        <div className="dashboard-scroll">
          <button className="today-chip" type="button">
            Today
          </button>
          <HeroCard />
          <StatusCard statusItems={mockDashboardData.statusItems} />
          <TripCard countdown={mockDashboardData.koreaTripCountdown} />
          <CalendarSection
            currentMonth={mockDashboardData.currentMonth}
            calendarDays={mockDashboardData.calendarDays}
            upcomingSchedule={mockDashboardData.upcomingSchedule}
          />
        </div>
        <BottomNavigation items={mockDashboardData.bottomNavItems} onMockNavigate={onMockNavigate} />
      </div>
    </main>
  );
}
