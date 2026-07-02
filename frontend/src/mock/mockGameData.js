export const MOCK_GAME_FILTERS = [
  { id: 'mock-filter-all', label: 'All', active: true },
  { id: 'mock-filter-campus', label: 'Campus', icon: 'campus' },
  { id: 'mock-filter-daily-life', label: 'Daily Life', icon: 'dailyLife' },
  { id: 'mock-filter-travel', label: 'Travel', icon: 'travel' },
  { id: 'mock-filter-weather', label: 'Weather', icon: 'weather' },
  { id: 'mock-filter-shopping', label: 'Shopping', icon: 'shopping' },
];

export const MOCK_ROLEPLAY_GAMES = [
  {
    id: 'mock-roleplay-first-day-college',
    title: '1. First Day at College',
    description: 'Borrow an eraser from a classmate.',
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '5 min',
    imageSrc: '/roleplay_title_images/first_day_at_colleage.png',
    imageAlt: 'Student in a college classroom borrowing an eraser',
  },
  {
    id: 'mock-roleplay-apple',
    title: '2. I Want an Apple!',
    description: 'Ask for the fruit you want to eat.',
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '5 min',
    imageSrc: '/roleplay_title_images/i_want_an_apple.png',
    imageAlt: 'Student buying an apple at a fruit stand',
  },
  {
    id: 'mock-roleplay-schedule',
    title: "3. Today's Schedule",
    description: "Check and confirm today's plan.",
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '6 min',
    imageSrc: '/roleplay_title_images/today_s_schedule.png',
    imageAlt: 'Student checking a campus schedule board',
  },
  {
    id: 'mock-roleplay-bus-stop',
    title: '4. Where Is the Bus Stop?',
    description: 'Ask for directions to the bus stop.',
    difficulty: 'Medium',
    difficultyTone: 'medium',
    duration: '7 min',
    imageSrc: '/roleplay_title_images/where_is_the_bust_stop.png',
    imageAlt: 'Student asking for directions near a bus stop sign',
  },
  {
    id: 'mock-roleplay-rain',
    title: '5. Looks Like Rain',
    description: 'Talk about the weather and what may happen.',
    difficulty: 'Medium',
    difficultyTone: 'medium',
    duration: '6 min',
    imageSrc: '/roleplay_title_images/looks_like_rain.png',
    imageAlt: 'Student holding an umbrella under rainy skies',
  },
  {
    id: 'mock-roleplay-price',
    title: '6. How Much Is This?',
    description: 'Ask the price of an item.',
    difficulty: 'Easy',
    difficultyTone: 'easy',
    duration: '5 min',
    imageSrc: '/roleplay_title_images/how_much_is_this.png',
    imageAlt: 'Student asking a shop clerk about an item price',
  },
];

export function getMockGameData() {
  return {
    profileInitial: 'H',
    filters: MOCK_GAME_FILTERS,
    roleplayGames: MOCK_ROLEPLAY_GAMES,
  };
}
