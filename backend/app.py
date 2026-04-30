import os
import json
import uuid
import re
import time
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

groq_client = Groq(api_key=GROQ_API_KEY)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["learnify"]
subjects_col = db["subjects"]
results_col  = db["results"]

MODEL_NAME = "llama-3.3-70b-versatile"
rate_limit_store = {}


# ─────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────

def get_subject_doc(subject):
    return subjects_col.find_one({"name": subject}, {"_id": 0})


def check_rate_limit(ip_address):
    current_time = time.time()

    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = []

    rate_limit_store[ip_address] = [
        timestamp for timestamp in rate_limit_store[ip_address]
        if current_time - timestamp < 60
    ]

    if len(rate_limit_store[ip_address]) >= 10:
        return False

    rate_limit_store[ip_address].append(current_time)
    return True


def validate_subject(subject, topic):
    doc = get_subject_doc(subject)
    if not doc:
        return False, f"Invalid subject: {subject}"
    if topic not in doc["topics"]:
        return False, f"Invalid topic: {topic}"
    return True, None


def get_subject_nature(subject):
    doc = get_subject_doc(subject)
    if doc:
        return doc.get("nature", "theoretical")
    return "theoretical"


# ─────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────

def build_prompt(subject, topic, subtopics, question_type, difficulty, num_questions):
    subject_nature = get_subject_nature(subject)

    if question_type == "mixed":
        mcq_count = round(num_questions * 0.5)
        scenario_count = round(num_questions * 0.3)
        short_count = num_questions - mcq_count - scenario_count
        mix_instruction = (
            f"   - mixed: YOU MUST GENERATE EXACTLY:\n"
            f"     * {mcq_count} questions of type 'mcq'\n"
            f"     * {scenario_count} questions of type 'scenario_based'\n"
            f"     * {short_count} questions of type 'short_answer'\n"
            f"     NO deviation allowed. Strict counts enforced."
        )
    else:
        mix_instruction = (
            f"   - ALL {num_questions} questions MUST be type '{question_type}'. No exceptions."
        )

    prompt = f"""You are a university exam paper setter with expertise in {subject}.

Subject: {subject}
Topic: {topic}
Subtopics: {', '.join(subtopics)}
Question Type: {question_type}
Difficulty: {difficulty}
Number of Questions: {num_questions}

CRITICAL INSTRUCTIONS:
1. Analyze the subject nature: This is a {subject_nature} subject.
2. Difficulty Guidelines:
   - Easy: Fundamental concepts, definitions, basic application
   - Medium: Conceptual understanding, analytical thinking, problem-solving
   - Hard: Advanced application, complex scenarios, multi-step reasoning

3. Question Type Requirements:
{mix_instruction}

4. Quality Standards:
   - Avoid trivial questions unless difficulty is Easy
   - For Medium/Hard: Focus on deep conceptual understanding and application
   - Ensure questions test understanding, not just memorization
   - For code-based: Use realistic, practical code examples
   - For scenario-based: Create realistic business/technical scenarios

5. JSON Structure Requirements:
   - Each question MUST have "type" field: mcq | definition | short_answer | scenario_based | code_based
   - Include "options" array ONLY if type = mcq (4 options with structure: {{"key": "A", "text": "option text"}})
   - Include "code_snippet" ONLY if type = code_based
   - Include "case_study" ONLY if type = scenario_based
   - Always include "correct_answer" (for MCQ use letter: A/B/C/D, for others use complete answer)
   - YOU MUST GENERATE EXACTLY {num_questions} questions, no more, no less

Generate ONLY valid JSON. No markdown, no explanations, no code blocks.

Return format:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq|definition|short_answer|scenario_based|code_based",
      "question": "Question text here",
      "code_snippet": null,
      "case_study": null,
      "options": null,
      "correct_answer": "Answer here"
    }}
  ]
}}"""

    return prompt


# ─────────────────────────────────────────────
# GROQ + JSON HELPERS
# ─────────────────────────────────────────────

def call_groq(prompt):
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a university exam paper setter. You generate high-quality, academically rigorous questions. You ALWAYS respond with valid JSON only, no markdown formatting, no code blocks, no explanations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq API error: {str(e)}")
        raise Exception("Failed to generate quiz questions")


def extract_json(response_text):
    try:
        response_text = response_text.strip()
        parsed = json.loads(response_text)

        if "questions" not in parsed:
            raise ValueError("Response missing 'questions' field")

        return parsed["questions"]
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        raise ValueError("Failed to parse AI response")
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        raise ValueError("Failed to process AI response")


def validate_questions(questions, question_type):
    for idx, q in enumerate(questions):
        if "type" not in q:
            raise ValueError(f"Question {idx + 1} missing 'type' field")

        if "question" not in q:
            raise ValueError(f"Question {idx + 1} missing 'question' field")

        if "correct_answer" not in q:
            raise ValueError(f"Question {idx + 1} missing 'correct_answer' field")

        if question_type == "mcq" and q["type"] != "mcq":
            raise ValueError(f"Question {idx + 1} must be MCQ type when question_type is 'mcq'")

        if q["type"] == "mcq":
            if not q.get("options"):
                raise ValueError(f"Question {idx + 1} is MCQ but missing options")

            if not isinstance(q["options"], list):
                raise ValueError(f"Question {idx + 1} options must be a list")

            if len(q["options"]) != 4:
                raise ValueError(f"Question {idx + 1} must have exactly 4 options")

            keys_found = []
            for opt in q["options"]:
                if not isinstance(opt, dict):
                    raise ValueError(f"Question {idx + 1} options must be objects with 'key' and 'text'")

                if "key" not in opt or "text" not in opt:
                    raise ValueError(f"Question {idx + 1} each option must have 'key' and 'text' fields")

                keys_found.append(opt["key"])

            if sorted(keys_found) != ["A", "B", "C", "D"]:
                raise ValueError(f"Question {idx + 1} must have options with keys A, B, C, D")

            if q["correct_answer"] not in ["A", "B", "C", "D"]:
                raise ValueError(f"Question {idx + 1} correct_answer must be A, B, C, or D")
        else:
            if q.get("options") is not None and q.get("options") != []:
                raise ValueError(f"Question {idx + 1} is not MCQ but has options field")

        if q["type"] == "code_based":
            if not q.get("code_snippet") or q.get("code_snippet") == "":
                raise ValueError(f"Question {idx + 1} is code_based but missing code_snippet")

        if q["type"] == "scenario_based":
            if not q.get("case_study") or q.get("case_study") == "":
                raise ValueError(f"Question {idx + 1} is scenario_based but missing case_study")


# ─────────────────────────────────────────────
# RESULT EVALUATION HELPER
# ─────────────────────────────────────────────

def normalize(text):
    """Lowercase, strip punctuation, collapse whitespace."""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return "Quiz Generator Backend is running!"


@app.route("/subjects", methods=["GET"])
def get_subjects():
    names = [doc["name"] for doc in subjects_col.find({}, {"_id": 0, "name": 1})]
    return jsonify({"subjects": names})


@app.route("/topics/<subject>", methods=["GET"])
def get_topics(subject):
    doc = get_subject_doc(subject)
    if not doc:
        return jsonify({"error": "Invalid subject"}), 400

    topics = [
        {"main_topic": k, "subtopics": v}
        for k, v in doc["topics"].items()
    ]
    return jsonify({"topics": topics})


@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    try:
        ip_address = request.remote_addr

        if not check_rate_limit(ip_address):
            return jsonify({"error": "Rate limit exceeded. Maximum 10 requests per minute."}), 429

        data = request.get_json()

        if data is None:
            return jsonify({"error": "Invalid JSON body"}), 400

        subject = data.get("subject")
        topic = data.get("topic")
        question_type = data.get("question_type")
        difficulty = data.get("difficulty")
        num_questions = data.get("num_questions")

        if not all([subject, topic, question_type, difficulty, num_questions]):
            return jsonify({"error": "Missing required fields"}), 400

        if question_type not in ["mcq", "definition", "short_answer", "scenario_based", "code_based", "mixed"]:
            return jsonify({"error": "Invalid question type"}), 400

        if difficulty not in ["Easy", "Medium", "Hard"]:
            return jsonify({"error": "Invalid difficulty"}), 400

        if num_questions not in [5, 10, 15]:
            return jsonify({"error": "Invalid number of questions"}), 400

        is_valid, error_msg = validate_subject(subject, topic)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        doc = get_subject_doc(subject)
        all_subtopics = doc["topics"][topic]

        # use selected subtopics if sent, else use all
        selected_subtopics = data.get("selected_subtopics")
        if selected_subtopics and isinstance(selected_subtopics, list) and len(selected_subtopics) > 0:
            subtopics = [s for s in selected_subtopics if s in all_subtopics]
            if not subtopics:
                return jsonify({"error": "Selected subtopics not valid for this topic"}), 400
        else:
            subtopics = all_subtopics

        prompt = build_prompt(subject, topic, subtopics, question_type, difficulty, num_questions)

        groq_response = call_groq(prompt)
        questions = extract_json(groq_response)

        if len(questions) != num_questions:
            print(f"Question count mismatch: expected {num_questions}, got {len(questions)}. Retrying...")
            groq_response = call_groq(prompt)
            questions = extract_json(groq_response)

            if len(questions) != num_questions:
                return jsonify({"error": "LLM returned incorrect number of questions"}), 400

        validate_questions(questions, question_type)

        quiz_id = str(uuid.uuid4())

        quiz_data = {
            "quiz_id": quiz_id,
            "subject": subject,
            "topic": topic,
            "subtopics": subtopics,
            "difficulty": difficulty,
            "question_type": question_type,
            "num_questions": num_questions,
            "questions": questions
        }

        return jsonify(quiz_data), 200

    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({"error": "An error occurred while generating the quiz"}), 500


@app.route("/submit-quiz", methods=["POST"])
def submit_quiz():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON body"}), 400

        questions = data.get("questions")
        answers = data.get("answers")  # list of {"id": 1, "answer": "A"}
        username = data.get("username")  # logged-in user from localStorage

        if not questions or not answers:
            return jsonify({"error": "Missing 'questions' or 'answers'"}), 400

        if len(answers) != len(questions):
            return jsonify({"error": "Answer count must match question count"}), 400

        answer_map = {str(a["id"]): a["answer"] for a in answers}

        results = []
        correct_count = 0

        for q in questions:
            qid = str(q["id"])
            user_ans = answer_map.get(qid, "")
            correct_ans = q.get("correct_answer", "")
            q_type = q.get("type", "")

            if q_type == "mcq":
                is_correct = str(user_ans).strip().upper() == str(correct_ans).strip().upper()
            else:
                norm_user = normalize(user_ans)
                norm_correct = normalize(correct_ans)
                is_correct = norm_user == norm_correct or norm_user in norm_correct

            if is_correct:
                correct_count += 1

            results.append({
                "id": q["id"],
                "type": q_type,
                "question": q["question"],
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct
            })

        total = len(questions)
        percentage = round((correct_count / total) * 100, 1)

        results_col.insert_one({
            "username":    username,
            "quiz_id":    data.get("quiz_id"),
            "subject":    data.get("subject"),
            "topic":      data.get("topic"),
            "subtopics":  data.get("subtopics"),
            "difficulty": data.get("difficulty"),
            "score":      correct_count,
            "total":      total,
            "percentage": percentage,
            "results":    results,
            "submitted_at": time.time()
        })

        return jsonify({
            "score": correct_count,
            "total": total,
            "percentage": percentage,
            "results": results
        }), 200

    except Exception as e:
        print(f"Submit quiz error: {str(e)}")
        return jsonify({"error": "Failed to evaluate quiz"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)