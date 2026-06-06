import { useState } from 'react';
import DashboardMainPage from './views/DashboardMainPage.jsx';
import GameMainPage from './views/GameMainPage.jsx';

export default function App() {
  const [activeMockTab, setActiveMockTab] = useState('dashboard');

  if (activeMockTab === 'game') {
    return <GameMainPage onMockNavigate={setActiveMockTab} />;
  }

  return <DashboardMainPage onMockNavigate={setActiveMockTab} />;
}
