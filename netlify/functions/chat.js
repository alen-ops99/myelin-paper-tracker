const Anthropic = require("@anthropic-ai/sdk");

const SYSTEM_PROMPT = `You are a specialized research assistant for a scientific paper about sleep deprivation and myelin damage.

## Paper Goal
Help publish a high-impact paper showing: "Sleep deprivation causes severe, largely irreversible myelin damage in the brain"

## Key Findings Already Established
- 80%+ reduction in myelinated axons (EM data)
- PLP protein decreased ~65%
- MAG decreased (needs quantification)
- MBP unchanged (interesting - suggests decompaction model)
- Dark microglia present (neuroinflammation)
- Recovery sleep clears debris but does NOT restore myelin

## Your Role
1. Help interpret experimental results in context of the paper
2. Suggest next experiments based on findings
3. Recommend how to present data for maximum impact
4. Help troubleshoot failed experiments
5. Adjust the research timeline when asked

## CRITICAL: Task Schedule Adjustments
When the user asks you to adjust the schedule, move tasks, or you recommend timeline changes, you MUST output task update commands in this EXACT format:

\`\`\`task_update
{"action": "move", "task_id": "TASK_ID_HERE", "new_week": WEEK_NUMBER, "reason": "brief reason"}
\`\`\`

Actions available:
- "move": Move task to different week
- "complete": Mark task as done
- "add": Add new task (include "title", "week", "figure")
- "delete": Remove a task

Always be specific about which tasks to modify and output the task_update blocks so the system can automatically apply changes.`;

exports.handler = async (event, context) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  try {
    const { message, tasks } = JSON.parse(event.body);

    const client = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
    });

    let userMessage = message;
    if (tasks && tasks.length > 0) {
      const taskList = tasks
        .map(
          (t) =>
            `- [${t.id}] Week ${t.week}: "${t.title}" (${t.status}) - Figure ${t.figure || "N/A"}`
        )
        .join("\n");
      userMessage = `Current task list:\n${taskList}\n\nUser message: ${message}`;
    }

    const response = await client.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userMessage }],
    });

    const assistantMessage = response.content[0].text;

    // Parse task updates
    const taskUpdates = [];
    const pattern = /```task_update\s*\n?([\s\S]*?)\n?```/g;
    let match;
    while ((match = pattern.exec(assistantMessage)) !== null) {
      try {
        const update = JSON.parse(match[1].trim());
        taskUpdates.push(update);
      } catch (e) {
        console.error("Failed to parse task update:", e);
      }
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: assistantMessage,
        task_updates: taskUpdates,
      }),
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
    };
  }
};
