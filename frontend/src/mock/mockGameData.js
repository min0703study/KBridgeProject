export const MOCK_GAME_FILTERS = [
  { id: 'mock-filter-all', label: 'All', active: true },
  { id: 'mock-filter-retail', label: 'Retail', icon: 'retail' },
  { id: 'mock-filter-dining', label: 'Dining', icon: 'dining' },
  { id: 'mock-filter-hospitality', label: 'Hospitality', icon: 'hospitality' },
  { id: 'mock-filter-resort', label: 'Resort', icon: 'resort' },
  { id: 'mock-filter-manufacturing', label: 'Manufacturing', icon: 'manufacturing' },
  { id: 'mock-filter-beginner', label: 'Beginner', icon: 'beginner' },
];

export const MOCK_ROLEPLAY_GAMES = [
  {
    id: 'mock-roleplay-convenience-store',
    title: 'Convenience Store',
    description: 'Buy snacks and pay at the counter.',
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '5 min',
    imageSrc: '/roleplay_title_image/roleplay_convenience_store_customer.png',
    imageAlt: 'Student buying snacks at a convenience store',
  },
  {
    id: 'mock-roleplay-restaurant',
    title: 'Restaurant',
    description: 'Order food and ask for recommendations.',
    difficulty: 'Medium',
    difficultyTone: 'medium',
    duration: '7 min',
    imageSrc: '/roleplay_title_image/roleplay_restaurant_customer.png',
    imageAlt: 'Customer reading a menu in a restaurant',
  },
  {
    id: 'mock-roleplay-hotel',
    title: 'Hotel',
    description: 'Check in and ask for room help.',
    difficulty: 'Medium',
    difficultyTone: 'medium',
    duration: '6 min',
    imageSrc: '/roleplay_title_image/roleplay_hotel_customer.png',
    imageAlt: 'Student checking in at a hotel',
  },
  {
    id: 'mock-roleplay-resort',
    title: 'Resort',
    description: 'Ask about amenities and enjoy your stay.',
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '6 min',
    imageSrc: '/roleplay_title_image/roleplay_resort_customer.png',
    imageAlt: 'Resort guest holding a drink on the beach',
  },
  {
    id: 'mock-roleplay-factory',
    title: 'Factory Visit',
    description: 'Join a tour and ask safety questions.',
    difficulty: 'Hard',
    difficultyTone: 'hard',
    duration: '8 min',
    imageSrc: '/roleplay_title_image/roleplay_factory_visit_customer.png',
    imageAlt: 'Student visiting a factory with a tablet',
  },
  {
    id: 'mock-roleplay-cafe',
    title: 'Cafe',
    description: 'Order your favorite drink like a local.',
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '5 min',
    imageSrc: '/roleplay_title_image/roleplay_cafe_customer.png',
    imageAlt: 'Customer drinking coffee in a cafe',
  },
];

export const MOCK_GAME_BOTTOM_NAV_ITEMS = [
  {
    id: 'mock-nav-homework',
    tab: 'homework',
    label: 'Homework',
    iconSrc: '/08_nav_homework_note.png',
    iconAlt: 'Homework',
  },
  {
    id: 'mock-nav-vocabulary',
    tab: 'vocabulary',
    label: 'Vocabulary',
    iconSrc: '/09_nav_vocabulary_book_aa.png',
    iconAlt: 'Vocabulary',
  },
  {
    id: 'mock-nav-dashboard',
    tab: 'dashboard',
    label: 'Dashboard',
    lucide: 'dashboard',
  },
  {
    id: 'mock-nav-game',
    tab: 'game',
    label: 'Game',
    lucide: 'game',
    active: true,
  },
  {
    id: 'mock-nav-settings',
    tab: 'settings',
    label: 'Settings',
    iconSrc: '/10_nav_settings_gear.png',
    iconAlt: 'Settings',
  },
];

export function getMockGameData() {
  return {
    profileInitial: 'H',
    filters: MOCK_GAME_FILTERS,
    roleplayGames: MOCK_ROLEPLAY_GAMES,
    bottomNavItems: MOCK_GAME_BOTTOM_NAV_ITEMS,
  };
}
