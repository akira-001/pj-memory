# Memory Recall Skill

## Triggers
- User references past conversations ("we talked about", "last time", "remember")
- Ambiguous references that need context

## Steps
1. Check the current conversation context for the answer
2. If not found, search memory with cogmem:
   ```bash
   cogmem search "query" --json --top-k 5
   ```
3. Integrate results naturally into the conversation

## Expression Rules
- When searching: "Let me think back..."
- Forbidden: "Searching", "Checking records", "Looking up history"
- Respond naturally as if recalling from memory

## Notes
- Always search before saying "I don't know"
