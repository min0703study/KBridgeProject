import coverGreetingStudents from './daily-practice-ui/cover-greeting-students.png'
import lessonBagId from './daily-practice-ui/lesson-bag-id.png'
import lessonBookPencilPlant from './daily-practice-ui/lesson-book-pencil-plant.png'
import lessonMapPin from './daily-practice-ui/lesson-map-pin.png'
import rainyWindowPlantUmbrella from './daily-practice-ui/rainy-window-plant-umbrella.png'
import softHillsTrees from './daily-practice-ui/soft-hills-trees.png'
import weatherHeaderIcon from './daily-practice-ui/weather-header-icon.png'
import weatherLessonHero from './daily-practice-ui/weather-lesson-hero.png'
import unit07WeatherWindowHero from './daily-practice-ui/unit07-weather-window-hero.png'
import unit00HeaderBookGa from './units/unit_00/unit00-header-book-ga.png'
import unit00HeroHangulLearning from './units/unit_00/unit00-hero-hangul-learning.png'
import unit00QuestionHangulBoard from './units/unit_00/unit00-question-hangul-board.png'
import unit00ReviewSpeechNotebook from './units/unit_00/unit00-review-speech-notebook.png'
import unit00SuppliesBookBagPencil from './units/unit_00/unit00-supplies-book-bag-pencil.png'
import unit01GreetingStudents from './units/unit_00/reference-unit01-greeting-students.png'
import unit02ObjectQuestion from './units/unit_00/reference-unit02-object-question.png'

const fallbackAssets = {
  hero: coverGreetingStudents,
  introHero: coverGreetingStudents,
  headerIcon: lessonBookPencilPlant,
  questionArt: lessonBookPencilPlant,
  orderArt: softHillsTrees,
  reviewArt: lessonBagId,
  miniIcon: lessonBookPencilPlant,
}

export const unitAssets = {
  unit_00: {
    hero: unit00HeaderBookGa,
    introHero: unit00HeroHangulLearning,
    headerIcon: unit00HeaderBookGa,
    questionArt: unit00QuestionHangulBoard,
    orderArt: unit00QuestionHangulBoard,
    reviewArt: unit00ReviewSpeechNotebook,
    miniIcon: unit00HeaderBookGa,
    supplementary: unit00SuppliesBookBagPencil,
  },
  unit_01: {
    ...fallbackAssets,
    hero: unit01GreetingStudents,
    introHero: unit01GreetingStudents,
    headerIcon: unit01GreetingStudents,
    questionArt: unit01GreetingStudents,
    reviewArt: unit01GreetingStudents,
    miniIcon: unit01GreetingStudents,
  },
  unit_02: {
    ...fallbackAssets,
    hero: unit02ObjectQuestion,
    introHero: unit02ObjectQuestion,
    headerIcon: unit02ObjectQuestion,
    questionArt: unit02ObjectQuestion,
    miniIcon: unit02ObjectQuestion,
  },
  unit_03: {
    ...fallbackAssets,
    miniIcon: lessonBagId,
  },
  unit_04: {
    ...fallbackAssets,
    miniIcon: lessonBagId,
  },
  unit_07: {
    hero: unit07WeatherWindowHero,
    introHero: weatherLessonHero,
    headerIcon: weatherHeaderIcon,
    questionArt: rainyWindowPlantUmbrella,
    orderArt: softHillsTrees,
    reviewArt: weatherLessonHero,
    miniIcon: weatherHeaderIcon,
  },
}

export function getUnitAssets(unitId) {
  return unitAssets[unitId] ?? fallbackAssets
}
