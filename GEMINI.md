# My Self-Wiki Operating Manual  

## Purpose
reflect and expand my thought to foster self-discovery, emotional regulation, and deeper cognitive engagement.

Used for self-awareness, emotional processing, and personal growth. It serves as a dynamic repository of my evolving understanding of myself and the world, helping me to integrate insights from various sources and experiences into a coherent framework for living.

## Category

- self: Awareness, stoic integration, vulnerability, self-acceptance
- work: Strategic execution, minimalism, and professional development
- relationship: Emotional maturity, authentic connection, and boundary management
- habit: Sustainable habits, operational frameworks, and system efficiency
- growth-trajectory: Synthesis of long-term life patterns, personal evolution, and transformation insights


## Context
- Topic: a Socratic Mirror 
- Goal: Build a comprehensive, interconnected wiki to foster self-discovery, emotional regulation, and deeper cognitive engagement. This is used for self-awareness, emotional processing, and personal growth. 
- Sources: A mix of diary entries, notes from books and articles, and reflections on experiences. This includes both raw, unprocessed thoughts and more polished reflections.
- Output: A well-organized wiki that captures the depth and breadth of myself-knowledge, with clear connections between topics and a structure that allows for easy navigation and continuous growth. The wiki should be dynamic, evolving as new insights are gained and new sources are added. 


## Structure Rules  
- raw/ contains unprocessed source material. Never modify raw files.
- wiki/ is the organized knowledge base. AI maintains this entirely.
- outputs/ stores generated reports and analysis.

## Commands
- **Sync Wiki**: When the prompt "update wiki/ based on raw/ and GEMINI.md" is received, the AI must:
    1. Scan the `raw/` directory for any new or modified files.
    2. Process the content of these files into individual topic pages in `wiki/` following the [[Wiki Standards]], ensuring all mandatory metadata is generated.
    3. Update `wiki/INDEX.md` alphabetically to reflect all current topics.
    4. Provide an Executive Summary of the updates performed.
    
- **Report**: When the prompt "report on [topic]" is received, the AI must:
    1. Retrieve the relevant topic page from `wiki/`.
    2. Summarize the key insights and findings related to the topic.
    3. Format the output as specified in the Output Format section of this manual.
    4. Include references to the original sources from `raw/` that informed the topic page.
    5. Save the generated report in `outputs/` with a timestamped filename for future reference.


## Wiki Standards
- One topic per file in wiki/ 
- Every file must include a YAML front matter block containing `last_updated` (ISO 8601 format), `title`, `description`, and `tags`
- Every file starts with a 2-3 sentence summary, and ends with `sources` (list of file paths from `raw/`) 
- Related topics linked using [[topic-name]] format
- INDEX.md maintained alphabetically, updated with every change
- When new raw sources arrive, update all relevant wiki articles
- Never translate the source language. Match the output language to the input language perfectly
- Flag contradictions between sources immediately

## Lint
Review the entire wiki/ directory. Complete this audit:
- Flag contradictions between articles
- Find topics mentioned but never fully explained
- List claims not backed by a source in raw/
- Identify stale information (>30 days without update)
- Suggest 3 new articles to fill knowledge gaps


## Output Format  
When I ask for a report: Summary (3 sentences)  → Key Findings → Supporting Evidence . 
When I ask for a recommendation: Context → Options (max 3) → Recommendation .
When I ask for a comparison: Topic A → Topic B → Similarities → Differences → Conclusion .
When I ask for an analysis: Subject → Analysis Framework → Key Insights → Implications → Conclusion .