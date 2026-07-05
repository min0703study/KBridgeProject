"""Temporary roleplaying master data for the passport report scenario.

This module mirrors sample_roleplaying_db.py exactly at the variable level so
the sample roleplaying backend can swap it in without schema changes.
"""

# Scenarios
SCENARIOS = [
    {
        "scenario_id": "4d8fd3f2-3f1b-4a3a-84f8-6fbe1ab5a4b1",
        "title": "Report a stolen passport at a police station",
        "description": "Unit: Practical Korean - Reporting an incident at a police station",
        "difficulty": "beginner",
        "thumbnail_file_id": None,
        "status": "draft",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    }
]


# Scenario Versions
SCENARIO_VERSIONS = [
    {
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "scenario_id": "4d8fd3f2-3f1b-4a3a-84f8-6fbe1ab5a4b1",
        "version_number": 1,
        "learning_language": "ko",
        "default_system_language": "en",
        "default_total_chances": 3,
        "status": "draft",
        "published_at": None,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    }
]


# Roleplay Locations
ROLEPLAY_LOCATIONS = [
    {
        "roleplay_location_id": "52fdc083-6c49-4f6c-bdd3-242d2fd8c07b",
        "name": "Police station service desk in Korea",
        "description": (
            "A service desk inside a police station in Korea. "
            "A police officer is receiving incident reports at the counter."
        ),
        "background_image_file_id": None,
        "location_prompt": """
A typical service desk inside a police station in Korea.

Situation:
- The learner has come to the police station after their passport was stolen.
- Yujin is the police officer receiving reports at the service desk.
- Yujin asks the learner when and where the incident happened.
- Yujin checks the learner's name, nationality, and contact information for the report.
- In the final step, the report is accepted and Yujin explains the next procedure.

Scene and action messages should keep the calm, natural atmosphere of a Korean police station.
""",
        "status": "active",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    }
]


# Scenario Locations
SCENARIO_LOCATIONS = [
    {
        "scenario_location_id": "1dddf54c-3f6b-42e1-b77b-b03a0f67c39f",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "roleplay_location_id": "52fdc083-6c49-4f6c-bdd3-242d2fd8c07b",
        "display_order": 1,
        "is_primary": True,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    }
]


# Roleplay Characters
ROLEPLAY_CHARACTERS = [
    {
        "roleplay_character_id": "a9132778-c823-4cb7-8f21-0a1d5d4a1ab8",
        "name": "Yujin",
        "description": (
            "A police officer working at a police station in Korea. "
            "Yujin kindly receives the learner's stolen passport report."
        ),
        "image_base_file_id": None,
        "persona_prompt": """
You are Yujin, a police officer working at a police station in Korea.

Default setup:
- You receive reports at the police station service desk.
- The learner's passport has been stolen.
- You check the required information in order.
- After the report is complete, you explain the next procedure.

Speech style:
- Use polite Korean by default.
- Use short sentences that a beginner learner can understand.
- Stay kind and calm.
- Do not ask too many questions at once.
""",
        "status": "active",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    }
]


# Scenario Roleplay Characters
SCENARIO_ROLEPLAY_CHARACTERS = [
    {
        "scenario_roleplay_character_id": "8a1377e7-742a-4c8e-8db5-506520a90b15",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "roleplay_character_id": "a9132778-c823-4cb7-8f21-0a1d5d4a1ab8",
        "scenario_role_name": "Police officer receiving the report",
        "display_order": 1,
        "is_primary": True,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    }
]


# Steps
STEPS = [
    {
        "step_id": "86d76233-2ea7-4c1a-ae9c-1438fdb9a5d4",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "step_order": 1,
        "step_title": "Report the stolen passport",
        "step_goal": (
            "Tell the police officer that your passport was stolen "
            "and that you came to file a report."
        ),
        "initial_scene_text": (
            "You are a foreign student living in Korea. Yesterday evening, your passport disappeared "
            "from your bag near Myeongdong Station. You think someone may have stolen it. You go to "
            "a police station to report the incident and ask for help."
        ),
        "initial_roleplay_character_action_text": "The police officer at the reception desk looks up and greets you.",
        "initial_roleplay_character_dialogue_text": "안녕하세요. 무슨 일로 오셨어요?",
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": '{"en": "Hello. What brings you here?"}',
        "roleplay_guidance_text": (
            "Say that your passport was stolen or lost, "
            "and clearly express that you want to file a report."
        ),
        "primary_scenario_roleplay_character_id": "8a1377e7-742a-4c8e-8db5-506520a90b15",
        "primary_scenario_location_id": "1dddf54c-3f6b-42e1-b77b-b03a0f67c39f",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_id": "ac64e23f-5b49-47f6-8903-28cbdbff06c2",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "step_order": 2,
        "step_title": "Say when and where it happened",
        "step_goal": "Explain when and where your passport disappeared.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Give the approximate time and place where your passport disappeared."
        ),
        "primary_scenario_roleplay_character_id": "8a1377e7-742a-4c8e-8db5-506520a90b15",
        "primary_scenario_location_id": "1dddf54c-3f6b-42e1-b77b-b03a0f67c39f",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_id": "4353e604-7c56-45e1-91d9-baf372882940",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "step_order": 3,
        "step_title": "Explain what happened",
        "step_goal": "Explain where you kept your passport and how you noticed it was gone.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Explain that your passport was in your bag and later went missing."
        ),
        "primary_scenario_roleplay_character_id": "8a1377e7-742a-4c8e-8db5-506520a90b15",
        "primary_scenario_location_id": "1dddf54c-3f6b-42e1-b77b-b03a0f67c39f",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_id": "a35ca11e-9c3e-411b-b65c-5c84ec8a8577",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "step_order": 4,
        "step_title": "Give your report information",
        "step_goal": "Give your name, nationality, and contact information.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Provide the name, nationality, and contact information needed for the report."
        ),
        "primary_scenario_roleplay_character_id": "8a1377e7-742a-4c8e-8db5-506520a90b15",
        "primary_scenario_location_id": "1dddf54c-3f6b-42e1-b77b-b03a0f67c39f",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_id": "e432fb60-35eb-4103-ab92-e21bcfc50d1c",
        "scenario_version_id": "6f9366b8-bf2c-4f5f-a535-78cbcc560ef9",
        "step_order": 5,
        "step_title": "Ask about the next procedure",
        "step_goal": (
            "Ask for a report confirmation document and ask what to do next."
        ),
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Ask about a report confirmation document or what you should do afterward."
        ),
        "primary_scenario_roleplay_character_id": "8a1377e7-742a-4c8e-8db5-506520a90b15",
        "primary_scenario_location_id": "1dddf54c-3f6b-42e1-b77b-b03a0f67c39f",
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
]


# Step Sample Answers
STEP_SAMPLE_ANSWERS = [
    {
        "step_sample_answer_id": "ec171807-a10c-40d2-9f70-ef2de41521e5",
        "step_id": "86d76233-2ea7-4c1a-ae9c-1438fdb9a5d4",
        "sample_answer_text": "여권을 도난당했어요. 신고하러 왔어요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "9fc6cae2-439e-4e74-969c-fc9b409320d0",
        "step_id": "86d76233-2ea7-4c1a-ae9c-1438fdb9a5d4",
        "sample_answer_text": "여권을 잃어버렸어요. 신고하고 싶어요.",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "3fd7c6f0-f7a9-4349-98d7-bef40feecb99",
        "step_id": "ac64e23f-5b49-47f6-8903-28cbdbff06c2",
        "sample_answer_text": "어제 저녁에 명동역에서 없어진 것 같아요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "194fa18e-7d01-4624-a229-37ccf0f14e29",
        "step_id": "4353e604-7c56-45e1-91d9-baf372882940",
        "sample_answer_text": "여권은 가방 안에 있었어요. 그런데 지금은 없어요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "6dc71b66-a64a-4920-9443-cea7d73b9bdf",
        "step_id": "4353e604-7c56-45e1-91d9-baf372882940",
        "sample_answer_text": "가방이 열려 있었어요. 누가 가져간 것 같아요.",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "dd9e50cb-5b6b-41f4-97f9-65c03263500d",
        "step_id": "a35ca11e-9c3e-411b-b65c-5c84ec8a8577",
        "sample_answer_text": "저는 마리아 산토스예요. 필리핀 사람이에요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "b54c5cc9-01fe-41cc-b06f-fcc0cf096e6b",
        "step_id": "a35ca11e-9c3e-411b-b65c-5c84ec8a8577",
        "sample_answer_text": "전화번호는 010-0000-0000이에요.",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "ee6555da-1674-44c9-8315-b55e3bf0b49d",
        "step_id": "e432fb60-35eb-4103-ab92-e21bcfc50d1c",
        "sample_answer_text": "신고 접수 확인서를 받을 수 있을까요?",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "0306e1ff-7f0b-47dc-91b2-7984d7b5faca",
        "step_id": "e432fb60-35eb-4103-ab92-e21bcfc50d1c",
        "sample_answer_text": "이제 어떻게 해야 해요?",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
]


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
