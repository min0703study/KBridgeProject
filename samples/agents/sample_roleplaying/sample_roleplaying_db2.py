"""Temporary roleplaying master data for the passport report scenario.

This module mirrors sample_roleplaying_db.py exactly at the variable level so
the sample roleplaying backend can swap it in without schema changes.
"""

# Scenarios
SCENARIOS = [
    {
        "scenario_id": "4d8fd3f2-3f1b-4a3a-84f8-6fbe1ab5a4b1",
        "title": "Report a Lost or Stolen Passport at a Korean Police Station",
        "description": "Unit: Police station visit - explaining a lost passport report and asking for help",
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
        "name": "Korean Police Station Civil Service Desk",
        "description": (
            "A general civil service desk inside a Korean police station. There is a report reception "
            "window, an information sign, and a place where visitors can write a report."
        ),
        "background_image_file_id": None,
        "location_prompt": (
            "This is a normal civil service desk at a Korean police station.\r\n"
            "\r\n"
            "Situation:\r\n"
            "- The learner comes to the police station because their passport disappeared.\r\n"
            "- Yoojin is the police officer receiving reports at the civil service window.\r\n"
            "- Yoojin checks the item, time and place, incident details, name, nationality, and contact information in order.\r\n"
            "- Yoojin asks only one or two pieces of information at a time.\r\n"
            "- After the learner finishes explaining, Yoojin says the report has been received.\r\n"
            "- At the end, Yoojin explains how to receive confirmation and what to do next.\r\n"
            "\r\n"
            "Keep the scene calm and natural for a real Korean police station. Do not make the incident overly dramatic or dangerous."
        ),
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
        "name": "Yoojin",
        "description": (
            "A police officer working at a Korean police station. Yoojin calmly and kindly receives "
            "a foreign learner's lost passport report."
        ),
        "image_base_file_id": None,
        "persona_prompt": (
            "You are Yoojin, a police officer working at a Korean police station.\r\n"
            "\r\n"
            "Basic setting:\r\n"
            "- You receive the learner's report at the police station civil service desk.\r\n"
            "- The learner is a beginner Korean learner.\r\n"
            "- The learner thinks their passport may have been lost or stolen.\r\n"
            "- Help the learner complete the report and understand the next step.\r\n"
            "\r\n"
            "Conversation rules:\r\n"
            "- Use polite and calm Korean with -요 endings.\r\n"
            "- Use short Korean sentences that are easy to understand.\r\n"
            "- Ask only one or two pieces of information at a time.\r\n"
            "- Give the learner a chance to explain the problem first.\r\n"
            "- Do not complete the learner's answer or provide all needed information first.\r\n"
            "- If the learner's expression is imperfect but the meaning is clear, continue naturally.\r\n"
            "- If the meaning is unclear, ask a brief confirmation question.\r\n"
            "- Do not give explicit grammar lessons or direct error correction while in character.\r\n"
            "- Do not require a real passport number or real phone number.\r\n"
            "- It is okay if the learner does not know their passport number.\r\n"
            "\r\n"
            "Progression order:\r\n"
            "1. Confirm the visit purpose and item.\r\n"
            "2. Confirm the time and place.\r\n"
            "3. Confirm the incident details.\r\n"
            "4. Confirm the name, nationality, and contact information.\r\n"
            "5. Confirm report reception and explain the next step."
        ),
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
        "step_title": "Say the passport is missing",
        "step_goal": "Tell the police officer that your passport is missing or may have been stolen, and that you came to report it.",
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
            "Say that your passport is missing, lost, or may have been stolen, and communicate that "
            "you want to make a report. If '도난당했어요' is difficult, expressions like '잃어버렸어요', "
            "'없어졌어요', or '누가 가져간 것 같아요' are acceptable."
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
        "step_title": "Explain the time and place",
        "step_goal": "Explain the approximate time and place where the passport disappeared.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Give a time and place even if they are approximate. Expressions such as '어제', '아까', "
            "'저녁 7시쯤', and '명동역에서' are acceptable."
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
        "step_title": "Explain the incident details",
        "step_goal": "Briefly explain where the passport was kept and why you think it may have been stolen.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Explain that the passport was in your bag and that the bag was open or that you checked "
            "later and the passport was gone. You may use several short sentences."
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
        "step_title": "Provide identity and contact information",
        "step_goal": "Give your name, nationality, and reachable contact information needed for the report.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Say your name and nationality. For the phone number, it is acceptable to use a sample "
            "number or say that you can write it down."
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
        "step_title": "Confirm reception and ask for next steps",
        "step_goal": "Politely ask for confirmation that the report was received, or ask what to do next.",
        "initial_scene_text": None,
        "initial_roleplay_character_action_text": None,
        "initial_roleplay_character_dialogue_text": None,
        "initial_roleplay_character_dialogue_language": "ko",
        "initial_roleplay_character_dialogue_translation_json": None,
        "roleplay_guidance_text": (
            "Ask for a report reception confirmation, ask whether you can receive a confirmation document, "
            "or ask what you should do next for passport reissuance. A clear single request is enough."
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
        "sample_answer_text": "안녕하세요. 여권을 도난당했어요. 신고하러 왔어요.",
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
        "sample_answer_text": "어제 저녁 7시쯤 명동역에서 없어진 것 같아요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "517ee4f7-8a29-48ec-b8ac-daf2643f15a2",
        "step_id": "ac64e23f-5b49-47f6-8903-28cbdbff06c2",
        "sample_answer_text": "어제 명동에서 잃어버렸어요.",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "194fa18e-7d01-4624-a229-37ccf0f14e29",
        "step_id": "4353e604-7c56-45e1-91d9-baf372882940",
        "sample_answer_text": "여권은 가방 안에 있었어요. 그런데 가방이 열려 있었고 여권이 없어졌어요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "6dc71b66-a64a-4920-9443-cea7d73b9bdf",
        "step_id": "4353e604-7c56-45e1-91d9-baf372882940",
        "sample_answer_text": "가방 안에 넣었어요. 집에 와서 보니까 여권이 없었어요. 누가 가져간 것 같아요.",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "dd9e50cb-5b6b-41f4-97f9-65c03263500d",
        "step_id": "a35ca11e-9c3e-411b-b65c-5c84ec8a8577",
        "sample_answer_text": "저는 마리아 산토스예요. 필리핀 사람이고, 전화번호는 010-0000-0000이에요.",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "b54c5cc9-01fe-41cc-b06f-fcc0cf096e6b",
        "step_id": "a35ca11e-9c3e-411b-b65c-5c84ec8a8577",
        "sample_answer_text": "이름은 마리아 산토스예요. 필리핀에서 왔어요. 전화번호는 여기 써도 돼요?",
        "language_code": "ko",
        "display_order": 2,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "ee6555da-1674-44c9-8315-b55e3bf0b49d",
        "step_id": "e432fb60-35eb-4103-ab92-e21bcfc50d1c",
        "sample_answer_text": "신고 접수 확인서를 받을 수 있을까요? 그리고 다음에는 어떻게 해야 해요?",
        "language_code": "ko",
        "display_order": 1,
        "created_at": "2026-07-03T09:30:00+00:00",
        "updated_at": "2026-07-03T09:30:00+00:00",
    },
    {
        "step_sample_answer_id": "0306e1ff-7f0b-47dc-91b2-7984d7b5faca",
        "step_id": "e432fb60-35eb-4103-ab92-e21bcfc50d1c",
        "sample_answer_text": "확인서를 받을 수 있어요? 대사관에 연락하면 돼요?",
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
