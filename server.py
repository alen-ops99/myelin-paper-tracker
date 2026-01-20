#!/usr/bin/env python3
"""
Myelin Paper Research Assistant Server
AI-powered project management for paper publication
"""

import os
import json
import re
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__, static_folder='static')
CORS(app)

# Data file path
DATA_FILE = Path(__file__).parent / 'project_data.json'

# System prompt for the AI assistant
SYSTEM_PROMPT = """You are a specialized research assistant helping Dr. Alen Juginovic publish a high-impact paper on "Sleep deprivation causes severe, largely irreversible myelin damage in the brain."

## Your Role
You are NOT a general chatbot. You are a focused research strategist whose ONLY goal is to help get this paper published in a top-tier journal (Cell Reports, Nature Communications, or PNAS).

## The Paper's Core Story
Sleep deprivation causes:
1. 80%+ loss of myelinated axons (EM data - COMPLETE)
2. Selective protein loss - PLP (~65% decrease) and MAG decreased, but MBP unchanged
3. Myelin decompaction visible in EM (COMPLETE)
4. Dark microglia showing neuroinflammation (COMPLETE)
5. Recovery sleep clears debris but does NOT restore myelin (COMPLETE)

## Figure Structure (4 Figures)
- Figure 1: EM phenotype (COMPLETE)
- Figure 2: Proteins + Lipids (IN PROGRESS)
- Figure 3: Cellular response (oligodendrocytes, neurons, microglia)
- Figure 4: Recovery failure

## How to Respond
- Be direct and strategic like a senior PI
- Always connect advice to the goal: getting published
- When the user shares results, interpret them and suggest next steps

## CRITICAL: Task Schedule Adjustments

When the user asks you to adjust the schedule, move tasks, or you recommend timeline changes, you MUST output task update commands.

**YOU MUST USE THE EXACT TASK IDs PROVIDED IN THE CURRENT TASKS LIST.**

For EACH task change, output a JSON block in this EXACT format:

```task_update
{"action": "move", "task_id": "EXACT_ID_FROM_LIST", "new_week": NUMBER, "reason": "why"}
```

```task_update
{"action": "complete", "task_id": "EXACT_ID_FROM_LIST", "reason": "why"}
```

```task_update
{"action": "add", "title": "New task name", "week": NUMBER, "priority": "high", "figure": NUMBER_OR_NULL, "reason": "why"}
```

```task_update
{"action": "delete", "task_id": "EXACT_ID_FROM_LIST", "reason": "why"}
```

**IMPORTANT RULES:**
1. When user says "auto-adjust", "adjust the schedule", "move tasks", etc. - YOU MUST output task_update blocks
2. Use the EXACT task_id from the task list provided (e.g., "mag-quant", "olig2-stain")
3. Output ONE task_update block per change
4. Changes are applied automatically - the user will see their schedule update in real-time
5. After outputting the changes, briefly explain what you adjusted and why

Example - if user says "move MAG quantification to week 2":
```task_update
{"action": "move", "task_id": "mag-quant", "new_week": 2, "reason": "User requested"}
```

Example - if user says "I finished the Olig2 staining":
```task_update
{"action": "complete", "task_id": "olig2-stain", "reason": "User completed"}
```
"""


def load_project_data():
    """Load project data from JSON file"""
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return get_default_data()


def save_project_data(data):
    """Save project data to JSON file"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_default_data():
    """Return default project structure"""
    return {
        "project_start": "2026-01-17",
        "deadline": "2026-03-17",
        "tasks": [
            {"id": "mag-quant", "title": "Quantify MAG Western blot (ImageJ)", "week": 1, "completed": False, "priority": "high", "figure": 2, "notes": ""},
            {"id": "cut-sections", "title": "Cut IHC sections from fixed tissue", "week": 1, "completed": False, "priority": "medium", "figure": 3, "notes": ""},
            {"id": "prep-massspec", "title": "Prepare brain samples for mass spec", "week": 1, "completed": False, "priority": "critical", "figure": 2, "notes": ""},
            {"id": "send-massspec", "title": "Send samples to mass spec core", "week": 1, "completed": False, "priority": "critical", "figure": 2, "notes": "BOTTLENECK"},
            {"id": "olig2-stain", "title": "Olig2 or CC1 IHC staining", "week": 2, "completed": False, "priority": "high", "figure": 3, "notes": ""},
            {"id": "degenerotag", "title": "DegeneroTag / FluoroJade staining", "week": 2, "completed": False, "priority": "high", "figure": 3, "notes": ""},
            {"id": "ihc-imaging", "title": "Image all IHC sections", "week": 3, "completed": False, "priority": "medium", "figure": 3, "notes": ""},
            {"id": "ihc-quant-start", "title": "Begin IHC quantification", "week": 3, "completed": False, "priority": "medium", "figure": 3, "notes": ""},
            {"id": "recovery-plp", "title": "Western blot: PLP on Recovery tissue", "week": 4, "completed": False, "priority": "high", "figure": 4, "notes": ""},
            {"id": "recovery-mag", "title": "Western blot: MAG on Recovery tissue", "week": 4, "completed": False, "priority": "high", "figure": 4, "notes": ""},
            {"id": "recovery-quant", "title": "Quantify recovery Western blots", "week": 4, "completed": False, "priority": "medium", "figure": 4, "notes": ""},
            {"id": "recovery-stats", "title": "Statistics: Non-SD vs SD vs Recovery", "week": 4, "completed": False, "priority": "medium", "figure": 4, "notes": ""},
            {"id": "ihc-quant-complete", "title": "Complete all IHC quantification", "week": 5, "completed": False, "priority": "high", "figure": 3, "notes": ""},
            {"id": "massspec-analyze", "title": "Analyze mass spec results", "week": 5, "completed": False, "priority": "high", "figure": 2, "notes": ""},
            {"id": "all-stats", "title": "Statistical analysis on all datasets", "week": 5, "completed": False, "priority": "high", "figure": None, "notes": ""},
            {"id": "fig1-final", "title": "Finalize Figure 1: EM Phenotype", "week": 6, "completed": False, "priority": "high", "figure": 1, "notes": ""},
            {"id": "fig2-final", "title": "Finalize Figure 2: Proteins + Lipids", "week": 6, "completed": False, "priority": "high", "figure": 2, "notes": ""},
            {"id": "fig3-final", "title": "Finalize Figure 3: Cellular Response", "week": 7, "completed": False, "priority": "high", "figure": 3, "notes": ""},
            {"id": "fig4-final", "title": "Finalize Figure 4: Recovery Failure", "week": 7, "completed": False, "priority": "high", "figure": 4, "notes": ""},
            {"id": "write-legends", "title": "Write figure legends", "week": 7, "completed": False, "priority": "medium", "figure": None, "notes": ""},
            {"id": "write-manuscript", "title": "Complete manuscript draft", "week": 8, "completed": False, "priority": "critical", "figure": None, "notes": ""},
            {"id": "coauthor-review", "title": "Circulate to co-authors", "week": 8, "completed": False, "priority": "high", "figure": None, "notes": ""},
            {"id": "submit", "title": "SUBMIT PAPER", "week": 8, "completed": False, "priority": "critical", "figure": None, "notes": ""}
        ],
        "figures": [
            {"id": 1, "title": "EM Phenotype", "status": "complete"},
            {"id": 2, "title": "Proteins + Lipids", "status": "in_progress"},
            {"id": 3, "title": "Cellular Response", "status": "not_started"},
            {"id": 4, "title": "Recovery Failure", "status": "partial"}
        ],
        "results": [],
        "chat_history": []
    }


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/data', methods=['GET'])
def get_data():
    """Get current project data"""
    return jsonify(load_project_data())


@app.route('/api/data', methods=['POST'])
def save_data_endpoint():
    """Save project data"""
    data = request.json
    save_project_data(data)
    return jsonify({"status": "saved"})


@app.route('/api/task/<task_id>', methods=['PATCH'])
def update_task(task_id):
    """Update a specific task"""
    data = load_project_data()
    updates = request.json

    for task in data['tasks']:
        if task['id'] == task_id:
            task.update(updates)
            break

    save_project_data(data)
    return jsonify({"status": "updated", "task": task})


@app.route('/api/auto-adjust', methods=['POST'])
def auto_adjust():
    """Automatically adjust task schedule based on current progress"""
    data = load_project_data()
    today = datetime.now()
    project_start = datetime.strptime(data['project_start'], '%Y-%m-%d')

    # Calculate current week
    days_passed = (today - project_start).days
    current_week = max(1, min(8, (days_passed // 7) + 1))

    # Get incomplete tasks that are scheduled before current week
    overdue = [t for t in data['tasks'] if not t['completed'] and t['week'] < current_week]

    # Move overdue tasks to current week
    for task in overdue:
        task['week'] = current_week

    # Redistribute remaining tasks
    incomplete = [t for t in data['tasks'] if not t['completed'] and t['week'] >= current_week]
    weeks_remaining = 8 - current_week + 1

    if weeks_remaining > 0 and len(incomplete) > 0:
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        incomplete.sort(key=lambda t: (t['week'], priority_order.get(t['priority'], 3)))

        # Spread across remaining weeks
        tasks_per_week = max(3, len(incomplete) // weeks_remaining)
        week = current_week
        count = 0

        for task in incomplete:
            for t in data['tasks']:
                if t['id'] == task['id']:
                    if count >= tasks_per_week and week < 8:
                        week += 1
                        count = 0
                    t['week'] = week
                    count += 1
                    break

    save_project_data(data)
    return jsonify({"status": "adjusted", "current_week": current_week, "data": data})


@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat with the AI research assistant"""
    user_message = request.json.get('message', '')
    data = load_project_data()

    # Build detailed task list with IDs for the AI
    task_list = []
    for t in data['tasks']:
        status = "DONE" if t['completed'] else f"Week {t['week']}"
        fig = f" (Fig {t['figure']})" if t.get('figure') else ""
        task_list.append(f"  - id=\"{t['id']}\" | {t['title']}{fig} | {status} | {t['priority']}")

    task_list_str = "\n".join(task_list)

    # Build context about current project state
    completed_count = len([t for t in data['tasks'] if t['completed']])
    pending_count = len([t for t in data['tasks'] if not t['completed']])

    # Calculate current week
    today = datetime.now()
    project_start = datetime.strptime(data['project_start'], '%Y-%m-%d')
    current_week = max(1, min(8, ((today - project_start).days // 7) + 1))

    context = f"""
## Current Project State (Week {current_week} of 8)

**Progress:** {completed_count} completed, {pending_count} pending

**CURRENT TASKS LIST (use these exact IDs for any adjustments):**
{task_list_str}

**Figure status:**
{chr(10).join([f"- Figure {f['id']} ({f['title']}): {f['status']}" for f in data['figures']])}

---
**User message:** {user_message}

REMEMBER: If the user asks you to adjust, move, or modify tasks, you MUST output ```task_update blocks with the exact task IDs from the list above. The system will automatically apply your changes.
"""

    # Get chat history (last 6 messages for context)
    chat_history = data.get('chat_history', [])[-6:]

    # Build messages for Claude
    messages = []
    for msg in chat_history:
        messages.append({"role": msg['role'], "content": msg['content']})
    messages.append({"role": "user", "content": context})

    try:
        # Load API key from environment
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            # Try loading from ~/.env
            env_file = Path.home() / '.env'
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if line.startswith('ANTHROPIC_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip('"\'')
                            break

        if not api_key:
            return jsonify({
                "response": "API key not found. Please set ANTHROPIC_API_KEY in your ~/.env file.",
                "error": True,
                "task_updates": []
            })

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        assistant_message = response.content[0].text

        # Save to chat history (save original user message, not the context-enriched one)
        data['chat_history'].append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})
        data['chat_history'].append({"role": "assistant", "content": assistant_message, "timestamp": datetime.now().isoformat()})

        # Parse task updates from response
        task_updates = []

        # Find all task_update blocks
        pattern = r'```task_update\s*\n?(.*?)\n?```'
        matches = re.findall(pattern, assistant_message, re.DOTALL)

        for match in matches:
            try:
                update = json.loads(match.strip())
                task_updates.append(update)

                # Apply the update
                action = update.get('action', '')

                if action == 'move':
                    task_id = update.get('task_id')
                    new_week = update.get('new_week')
                    if task_id and new_week:
                        for task in data['tasks']:
                            if task['id'] == task_id:
                                task['week'] = int(new_week)
                                print(f"Moved task {task_id} to week {new_week}")
                                break

                elif action == 'complete':
                    task_id = update.get('task_id')
                    if task_id:
                        for task in data['tasks']:
                            if task['id'] == task_id:
                                task['completed'] = True
                                print(f"Completed task {task_id}")
                                break

                elif action == 'add':
                    new_id = 'task-' + str(int(datetime.now().timestamp()))
                    new_task = {
                        'id': new_id,
                        'title': update.get('title', 'New Task'),
                        'week': int(update.get('week', current_week)),
                        'completed': False,
                        'priority': update.get('priority', 'medium'),
                        'figure': update.get('figure'),
                        'notes': update.get('reason', '')
                    }
                    data['tasks'].append(new_task)
                    print(f"Added new task: {new_task['title']}")

                elif action == 'delete':
                    task_id = update.get('task_id')
                    if task_id:
                        data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
                        print(f"Deleted task {task_id}")

            except json.JSONDecodeError as e:
                print(f"Failed to parse task update: {match} - {e}")
                continue

        # Save updated data
        save_project_data(data)

        # Clean the response for display (remove task_update blocks)
        clean_response = re.sub(r'```task_update\s*\n?.*?\n?```', '', assistant_message, flags=re.DOTALL)
        clean_response = clean_response.strip()

        return jsonify({
            "response": clean_response,
            "task_updates": task_updates,
            "error": False
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "response": f"Error communicating with AI: {str(e)}",
            "error": True,
            "task_updates": []
        })


@app.route('/api/result', methods=['POST'])
def log_result():
    """Log an experimental result"""
    data = load_project_data()
    result = request.json
    result['date'] = datetime.now().isoformat()

    if 'results' not in data:
        data['results'] = []
    data['results'].append(result)

    save_project_data(data)
    return jsonify({"status": "logged", "result": result})


if __name__ == '__main__':
    # Initialize data file if it doesn't exist
    if not DATA_FILE.exists():
        save_project_data(get_default_data())

    print("\n" + "="*50)
    print("Myelin Paper Research Assistant")
    print("="*50)
    print(f"\nOpen in browser: http://localhost:5050")
    print("\nPress Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5050, debug=True)
