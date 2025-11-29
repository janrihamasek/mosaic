# prompt_specification_compact_codex_instruction

Goal: Define a compact, uniform specification format for Codex task prompts.  
Context: Prompts are used to instruct Codex (VS Code agent) for implementing specific code or configuration changes in the Mosaic project. They must be concise, single-block plain text, and consistently structured for automation.  
Tasks:
1. Each prompt starts with an ID in the format # yymmdd_area_shortname (e.g., # 251102_frontend_tests_textencoder_polyfill).
2. Sections follow in fixed order: Goal, Context, Tasks, Output. 
3. No markdown formatting, blank lines, or code fences. 
4. Each section is written in clear technical English using short declarative sentences. 
5. All code snippets or commands appear inline without indentation or line breaks. 
6. Context summarizes problem and environment in ≤3 sentences. 
7. Tasks enumerate concrete implementation steps in one paragraph, separated by semicolons or numbered inline. 
8. Output describes the resulting changed or created files concisely. 
9. The entire prompt fits within ~10 lines and ≤800 characters.  
Output: A standardized single-block text prompt suitable for Codex input following the above structure.