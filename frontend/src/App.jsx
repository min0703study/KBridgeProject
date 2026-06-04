import { useState } from 'react';
import DashboardMainPage from './views/DashboardMainPage.jsx';
import GameMainPage from './views/GameMainPage.jsx';
import RoleplayInGamePage from './views/RoleplayInGamePage.jsx';

export default function App() {
  const [activeMockTab, setActiveMockTab] = useState('dashboard');

  if (activeMockTab === 'roleplay-convenience-store') {
    return <RoleplayInGamePage onMockBack={() => setActiveMockTab('game')} />;
  }

  if (activeMockTab === 'game') {
    return <GameMainPage onMockNavigate={setActiveMockTab} />;
  }

  return <DashboardMainPage onMockNavigate={setActiveMockTab} />;
}
