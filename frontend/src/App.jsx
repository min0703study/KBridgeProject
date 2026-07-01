import { useState } from 'react';
import DashboardMainPage from './views/DashboardMainPage.jsx';
import ChatbotMainPage from './views/ChatbotMainPage.jsx';
import HomeworkMainPage from './views/HomeworkMainPage.jsx';
import GameMainPage from './views/GameMainPage.jsx';

export default function App() {
  const [activeMockTab, setActiveMockTab] = useState('dashboard');

  if (activeMockTab === 'homework') {
    return <HomeworkMainPage onMockNavigate={setActiveMockTab} />;
  }

  if (activeMockTab === 'chatbot') {
    return <ChatbotMainPage onMockNavigate={setActiveMockTab} />;
  }

  if (activeMockTab === 'game') {
    return <GameMainPage onMockNavigate={setActiveMockTab} />;
  }
  
  return <DashboardMainPage onMockNavigate={setActiveMockTab} />;
}