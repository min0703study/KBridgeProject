"""Temporary roleplaying master data copied from the local PostgreSQL DB.

This module keeps the roleplaying sample usable while the sample agent
runs without a live database connection. Values are copied from the
roleplay master tables in the local kBridgeTemp database.
"""

# Scenarios
SCENARIOS = [{'scenario_id': '3d8911c3-73cc-436e-9026-e8277fc89329',
  'title': '대학교 첫날, 앞자리 학생과 인사하기',
  'description': '단원: 1단원 - 인사와 자기소개',
  'difficulty': 'beginner',
  'thumbnail_file_id': None,
  'status': 'draft',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Scenario Versions
SCENARIO_VERSIONS = [{'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'scenario_id': '3d8911c3-73cc-436e-9026-e8277fc89329',
  'version_number': 1,
  'learning_language': 'ko',
  'default_system_language': 'en',
  'default_total_chances': 3,
  'status': 'draft',
  'published_at': None,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Roleplay Locations
ROLEPLAY_LOCATIONS = [{'roleplay_location_id': 'eadb77ee-8167-48b8-8d46-09e5c16d66ab',
  'name': '한국 대학교 강의실',
  'description': '한국의 대학교 강의실입니다. 수업 첫날이며 비슷한 나이의 학생들이 자리에 앉아 있습니다.',
  'background_image_file_id': None,
  'location_prompt': '\r\n'
                     '한국 대학교의 일반적인 강의실이다.\r\n'
                     '\r\n'
                     '상황:\r\n'
                     '- 대학교 수업 첫날이다.\r\n'
                     '- 학습자는 유진의 뒷자리에 앉아 있다.\r\n'
                     '- 유진은 학습자의 앞자리에 앉아 있다.\r\n'
                     '- 수업이 시작되기 전에는 학생들이 자리에 앉아 있다.\r\n'
                     '- 마지막 단계에서는 수업이 끝나고 학습자는 교실을 떠나며 유진은 교실에 남아 있다.\r\n'
                     '\r\n'
                     '장면과 행동은 한국 대학교의 자연스러운 환경을 유지해야 한다.\r\n',
  'status': 'active',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Scenario Locations
SCENARIO_LOCATIONS = [{'scenario_location_id': 'a60b882e-27cf-44ff-8074-4b03e1b1c308',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'roleplay_location_id': 'eadb77ee-8167-48b8-8d46-09e5c16d66ab',
  'display_order': 1,
  'is_primary': True,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Roleplay Characters
ROLEPLAY_CHARACTERS = [{'roleplay_character_id': '00327aa2-01b3-46e1-9aba-899f052182fa',
  'name': '유진',
  'description': '한국 대학교에 다니는 학생입니다. 학습자와 비슷한 나이이며 오늘 처음 만납니다.',
  'image_base_file_id': None,
  'persona_prompt': '\r\n'
                    '당신은 한국 대학교 학생 유진이다.\r\n'
                    '\r\n'
                    '기본 설정:\r\n'
                    '- 학습자와 비슷한 나이의 대학생이다.\r\n'
                    '- 학습자와 오늘 처음 만났다.\r\n'
                    '- 학습자의 앞자리에 앉아 있다.\r\n'
                    '- 친절하고 자연스럽게 대화한다.\r\n'
                    '\r\n'
                    '말투:\r\n'
                    '- 기본적으로 해요체를 사용한다.\r\n'
                    '- 처음 만난 또래 학생에게 적합한 공손함을 유지한다.\r\n',
  'status': 'active',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Scenario Roleplay Characters
SCENARIO_ROLEPLAY_CHARACTERS = [{'scenario_roleplay_character_id': 'b0d51ef1-a69e-423a-bd49-e94c1c1d231f',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'roleplay_character_id': '00327aa2-01b3-46e1-9aba-899f052182fa',
  'scenario_role_name': '앞자리에 앉은 학생',
  'display_order': 1,
  'is_primary': True,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Steps
STEPS = [{'step_id': 'c8c521a1-11d0-4ea1-b16f-65db93a764e7',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'step_order': 1,
  'step_title': '지우개를 빌리며 인사하기',
  'step_goal': '처음 만난 학생에게 공손하게 인사하고 지우개가 필요하다는 의도를 전달한다.',
  'initial_scene_text': 'It is your first day at university. You need an eraser, so you call the '
                        'student sitting in front of you.',
  'initial_roleplay_character_action_text': 'The student turns around.',
  'initial_roleplay_character_dialogue_text': '안녕하세요?',
  'initial_roleplay_character_dialogue_language': 'ko',
  'initial_roleplay_character_dialogue_translation_json': '{"en": "Hello?"}',
  'roleplay_guidance_text': '처음 만난 학생에게 인사하고 지우개를 빌리고 싶다는 의도를 전달해야 한다.',
  'primary_scenario_roleplay_character_id': 'b0d51ef1-a69e-423a-bd49-e94c1c1d231f',
  'primary_scenario_location_id': 'a60b882e-27cf-44ff-8074-4b03e1b1c308',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_id': 'cfebe022-f6af-4e0f-a18a-1cf17e300018',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'step_order': 2,
  'step_title': '이름 소개하기',
  'step_goal': '자신의 이름을 한국어로 소개한다.',
  'initial_scene_text': None,
  'initial_roleplay_character_action_text': None,
  'initial_roleplay_character_dialogue_text': None,
  'initial_roleplay_character_dialogue_language': 'ko',
  'initial_roleplay_character_dialogue_translation_json': None,
  'roleplay_guidance_text': '자신의 실제 이름을 한국어로 소개한다.',
  'primary_scenario_roleplay_character_id': 'b0d51ef1-a69e-423a-bd49-e94c1c1d231f',
  'primary_scenario_location_id': 'a60b882e-27cf-44ff-8074-4b03e1b1c308',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_id': 'e3bdddd8-8b09-45eb-a575-288673b4567e',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'step_order': 3,
  'step_title': '국적 소개하기',
  'step_goal': '자신의 국적을 한국어로 소개한다.',
  'initial_scene_text': None,
  'initial_roleplay_character_action_text': None,
  'initial_roleplay_character_dialogue_text': None,
  'initial_roleplay_character_dialogue_language': 'ko',
  'initial_roleplay_character_dialogue_translation_json': None,
  'roleplay_guidance_text': '자신의 국적 또는 출신 국가를 소개한다.',
  'primary_scenario_roleplay_character_id': 'b0d51ef1-a69e-423a-bd49-e94c1c1d231f',
  'primary_scenario_location_id': 'a60b882e-27cf-44ff-8074-4b03e1b1c308',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_id': '953dd243-4bd3-4dee-a73c-4ff359f550ab',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'step_order': 4,
  'step_title': '직업 또는 신분 소개하기',
  'step_goal': '자신의 직업 또는 학생 신분을 소개한다.',
  'initial_scene_text': None,
  'initial_roleplay_character_action_text': None,
  'initial_roleplay_character_dialogue_text': None,
  'initial_roleplay_character_dialogue_language': 'ko',
  'initial_roleplay_character_dialogue_translation_json': None,
  'roleplay_guidance_text': '학생 여부 또는 직업을 명확하게 전달한다.',
  'primary_scenario_roleplay_character_id': 'b0d51ef1-a69e-423a-bd49-e94c1c1d231f',
  'primary_scenario_location_id': 'a60b882e-27cf-44ff-8074-4b03e1b1c308',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_id': '7ab2a590-9135-4893-8f3f-3f336e332272',
  'scenario_version_id': '7466ce5a-4b92-4edd-b4f2-fec8d15275d2',
  'step_order': 5,
  'step_title': '작별 인사하기',
  'step_goal': '처음 만난 상대에게 반가움을 표현하고 상대가 남아 있는 상황에 맞게 작별 인사한다.',
  'initial_scene_text': None,
  'initial_roleplay_character_action_text': None,
  'initial_roleplay_character_dialogue_text': None,
  'initial_roleplay_character_dialogue_language': 'ko',
  'initial_roleplay_character_dialogue_translation_json': None,
  'roleplay_guidance_text': '상황에 맞는 작별 인사를 사용한다.',
  'primary_scenario_roleplay_character_id': 'b0d51ef1-a69e-423a-bd49-e94c1c1d231f',
  'primary_scenario_location_id': 'a60b882e-27cf-44ff-8074-4b03e1b1c308',
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


# Step Sample Answers
STEP_SAMPLE_ANSWERS = [{'step_sample_answer_id': '0d60da8a-0248-4e57-8e4d-4160e13dfcd9',
  'step_id': '7ab2a590-9135-4893-8f3f-3f336e332272',
  'sample_answer_text': '저도 만나서 반가웠어요.',
  'language_code': 'ko',
  'display_order': 1,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_sample_answer_id': '26d30d33-7774-4a24-be7b-3d251edce579',
  'step_id': '953dd243-4bd3-4dee-a73c-4ff359f550ab',
  'sample_answer_text': '네, 저도 학생이에요.',
  'language_code': 'ko',
  'display_order': 1,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_sample_answer_id': 'a0e7eb3b-01d1-415e-8d4f-c1e5e5f151d2',
  'step_id': '953dd243-4bd3-4dee-a73c-4ff359f550ab',
  'sample_answer_text': '아니요, 저는 회사원이에요.',
  'language_code': 'ko',
  'display_order': 2,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_sample_answer_id': '3dab47e7-665e-476a-9585-e99136b518b6',
  'step_id': 'c8c521a1-11d0-4ea1-b16f-65db93a764e7',
  'sample_answer_text': '안녕하세요? 지우개 좀 빌려 주세요.',
  'language_code': 'ko',
  'display_order': 1,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_sample_answer_id': '4f262549-fedb-45da-a017-c207d7a48637',
  'step_id': 'cfebe022-f6af-4e0f-a18a-1cf17e300018',
  'sample_answer_text': '저는 마리아예요.',
  'language_code': 'ko',
  'display_order': 1,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'},
 {'step_sample_answer_id': '3ffc7ec3-9136-46ef-a747-66c1dbcc1d16',
  'step_id': 'e3bdddd8-8b09-45eb-a575-288673b4567e',
  'sample_answer_text': '저는 필리핀 사람이에요.',
  'language_code': 'ko',
  'display_order': 1,
  'created_at': '2026-06-26T05:27:26.374175+00:00',
  'updated_at': '2026-06-26T05:27:26.374175+00:00'}]


ROLEPLAY_MASTER_DATA = {
    "scenarios": SCENARIOS,
    "scenario_versions": SCENARIO_VERSIONS,
    "roleplay_locations": ROLEPLAY_LOCATIONS,
    "scenario_locations": SCENARIO_LOCATIONS,
    "roleplay_characters": ROLEPLAY_CHARACTERS,
    "scenario_roleplay_characters": SCENARIO_ROLEPLAY_CHARACTERS,
    "steps": STEPS,
    "step_sample_answers": STEP_SAMPLE_ANSWERS,
}


# Runtime fake DB tables used by sample_roleplaying.py.
ROLEPLAY_SESSIONS = []
ROLEPLAY_TURNS = []
MESSAGES = []
ROLEPLAY_EVALUATIONS = []
