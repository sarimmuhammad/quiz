import os
import json
import uuid
import re
import time
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)

SUBJECT_DATA = {
    "Analysis of Algorithms": {
        "Week 1: Introduction": [
            "Briefing on CLO's",
            "Role of algorithms in computing",
            "Analysis on nature of input and size of input",
            "Empirical vs Analytical Analysis",
            "PseudoCode"
        ],
        "Week 2: Sorting Algorithm analysis": [
            "Insertion Sort",
            "Loop Invariant & Correctness",
            "Bubble Sort"
        ],
        "Week 3: Asymptotic notations - Part 1": [
            "Big-O: Upper Bound",
            "Big Ω: Lower Bound"
        ],
        "Week 4: Asymptotic notations - Part 2": [
            "Big Θ: Upper and Lower Bound",
            "little-o",
            "little-ω"
        ],
        "Week 5: Recursion and recurrence relations": [
            "Recursion fundamentals",
            "Recurrence relations"
        ],
        "Week 6: Algorithm Design Techniques": [
            "Brute Force Approach"
        ],
        "Week 7: Divide-and-conquer approach": [
            "Divide-and-conquer paradigm",
            "Divide-and-conquer strategy"
        ],
        "Week 8: Advanced Sorting": [
            "Merge Sort",
            "Quick Sort"
        ],
        "Week 9: Greedy approach": [
            "Greedy method",
            "Greedy strategy"
        ],
        "Week 10: Dynamic programming": [
            "Elements of Dynamic Programming",
            "Dynamic Programming techniques"
        ],
        "Week 11: Search trees": [
            "Binary Search Trees",
            "Tree operations"
        ],
        "Week 12: Heaps and Hashing": [
            "Heaps",
            "Hashing"
        ],
        "Week 13: Graph algorithms": [
            "Graph algorithms fundamentals",
            "Shortest paths",
            "Sparse graphs"
        ],
        "Week 14: String matching": [
            "String matching algorithms"
        ],
        "Week 15: Complexity classes": [
            "Introduction to complexity classes"
        ]
    },
    "Introduction to Marketing": {
        "Week 1: Marketing in a changing World": [
            "Creating Customer Value and Satisfaction",
            "What is Marketing, Marketing Management",
            "Customer Needs, Wants, and Demands",
            "Market Offerings—Products, Services, and Experiences",
            "Marketing Management Philosophies",
            "Customer Value and Satisfaction"
        ],
        "Week 2: Customer-Driven Marketing Strategy": [
            "Designing a Customer-Driven Marketing Strategy",
            "Marketing Management Orientations",
            "Preparing an Integrated Marketing Plan and Program",
            "Building Customer Relationships",
            "Marketing Challenges in the New Connected Millennium",
            "Capturing Value from Customers",
            "The Changing Marketing Landscape"
        ],
        "Week 3: Company and Marketing Strategy": [
            "Partnering to Build Customer Relationships",
            "Company-Wide Strategic Planning",
            "Setting Company Objectives and Goals",
            "Designing the Business Portfolio",
            "Marketing Strategy and the Marketing Mix"
        ],
        "Week 4: Marketing Analysis and Planning": [
            "Marketing Analysis",
            "Marketing Planning",
            "Marketing Implementation",
            "Marketing Department Organization",
            "Marketing Control"
        ],
        "Week 5: Analyzing the Marketing Environment": [
            "The Microenvironment",
            "The Macro environment",
            "The Demographic, Economic, Natural Environment"
        ],
        "Week 6: Consumer Behavior": [
            "Responding to the Marketing Environment",
            "Consumer Markets and Consumer Buyer Behavior",
            "Model of Consumer Behavior",
            "Characteristics Affecting Consumer Behavior"
        ],
        "Week 7: Buyer Decision Process": [
            "Types of Buying Decision Behavior",
            "The Buyer Decision Process"
        ],
        "Week 8: Market Segmentation and Targeting": [
            "Customer-Driven Marketing Strategy",
            "Creating Value for Target Customers",
            "Market Segmentation",
            "Requirements for Effective Segmentation",
            "Market Targeting",
            "Differentiation and Positioning"
        ],
        "Week 9: Product & Services Strategy": [
            "What is Product",
            "Product Classifications",
            "Individual Product Decisions",
            "Product line decisions",
            "Product mix decisions"
        ],
        "Week 10: Marketing strategies for Service Firms": [
            "Marketing strategies for Service Firms",
            "Branding Strategy: Building Strong Brands",
            "Brand Equity"
        ],
        "Week 11: New-Product Development": [
            "New-Product Development",
            "Product Life Cycle strategies",
            "Managing New-Product Development",
            "Customer-Centered New-Product Development"
        ],
        "Week 12: Product Life Cycle and Pricing": [
            "Product life cycle strategies",
            "Marketing Strategies at every product life cycle stage",
            "New-Product Pricing Strategies",
            "Market-Skimming Pricing",
            "Market-Penetration Pricing",
            "Product Mix Pricing Strategies",
            "Price Adjustment Strategies"
        ],
        "Week 13: Marketing Channels and Promotion": [
            "Marketing Channels",
            "Number of channel level",
            "Conventional and vertical marketing channel",
            "Definition of wholesaler and retailer",
            "Promotion",
            "IMC, promotion mix, Advertising"
        ],
        "Week 14: Sales and E-business": [
            "Sales promotion, personal selling",
            "Public relations, Publicity",
            "Introduction to e-business",
            "Different trends"
        ],
        "Week 15: E-business and Digital Marketing": [
            "Rules of doing e-business",
            "E-business application in the market",
            "Digital Marketing",
            "Using analytics to interpret and optimize results to maximize performance"
        ]
    }
}
load_dotenv()
TECHNICAL_SUBJECTS = {"Analysis of Algorithms"}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")   # <-- yahan apni NEW key paste karo

groq_client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "llama-3.3-70b-versatile"

rate_limit_store = {}


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
    if subject not in SUBJECT_DATA:
        return False, f"Invalid subject: {subject}"
    
    if topic not in SUBJECT_DATA[subject]:
        return False, f"Invalid topic: {topic}"
    
    return True, None


def get_subject_nature(subject):
    if subject in TECHNICAL_SUBJECTS:
        return "technical"
    return "theoretical"


def build_prompt(subject, topic, subtopics, question_type, difficulty, num_questions):
    subject_nature = get_subject_nature(subject)
    
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
   - mcq: ALL questions MUST be multiple choice with 4 options
   - definition: Short theoretical questions requiring brief explanations
   - short_answer: Conceptual questions requiring detailed reasoning
   - scenario_based: Real-world case studies requiring analytical application
   - code_based: Include code snippets with questions (can be MCQ or short answer)
   - mixed: Intelligently mix formats based on subject nature:
     * Technical subjects: Include code-based ({'40%' if subject_nature == 'technical' else '0%'}), MCQ (30%), analytical (30%)
     * Theoretical subjects: Include scenario-based (40%), MCQ (30%), conceptual (30%)

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
            model="llama-3.3-70b-versatile",
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


@app.route("/subjects", methods=["GET"])
def get_subjects():
    return jsonify({
        "subjects": list(SUBJECT_DATA.keys())
    })


@app.route("/topics/<subject>", methods=["GET"])
def get_topics(subject):
    if subject not in SUBJECT_DATA:
        return jsonify({"error": "Invalid subject"}), 400
    
    topics = []
    for main_topic, subtopics in SUBJECT_DATA[subject].items():
        topics.append({
            "main_topic": main_topic,
            "subtopics": subtopics
        })
    
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
        
        subtopics = SUBJECT_DATA[subject][topic]
        
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


@app.route("/", methods=["GET"])
def index():
    return "Quiz Generator Backend is running!"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)