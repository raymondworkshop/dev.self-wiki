---
last_updated: 2024-05-29T00:00:00Z
title: AI Chatbot Development Principles
description: A framework detailing the differences between rule-based and AI chatbots, and the lifecycle stages for developing and deploying conversational AI systems.
tags: [type/principle, work, technology]
---

> This document outlines the architectural differences between various chatbot types (rule-based vs. AI) and maps out the necessary stages for developing, testing, and deploying a functional conversational AI agent. Successful implementation requires careful planning of dialogue flow, data collection strategies, and continuous monitoring.

## Evolution
- Initial concepts regarding chatbot types and development stages were synthesized from raw notes into a structured lifecycle model.

## Content

### Chatbot Types and Goals
The initial goal setting for any chatbot must define its intended function:
- **FAQ Chatbot**: Designed to handle frequently asked questions based on a predefined knowledge base.
- **Agent-like Bot**: A more advanced system capable of routing complex queries, requiring intuitive design.
- **Live Act Software**: A system capable of switching between automated chatbot responses and human intervention during real-time conversations.

### Development Lifecycle Stages

**1. Goal Setting:**
*   Define the specific role the chatbot will play (e.g., simple FAQ vs. complex problem solver).
*   Determine the intended user experience (intuitive and easy to use).

**2. Channel Selection:**
*   Decide on the medium (e.g., text-based chatbot).
*   Consider embedding options via API to support multiple communication channels.

**3. Dialogue Flow Design:**
*   This is critical: mapping out precisely what the bot will say at each conversational step.

**4. Data Collection:**
*   **Rule-Based Systems:** Collect data to establish patterns for predefined responses. The risk is a lack of answer if the input falls outside the programmed rules.
*   **AI Chatbots:** Require an initial training period. They must first analyze the user's request to identify intent and entities. Over time, they improve by observing the correctness of their responses. A large collection of interactions allows machine learning to map common questions to optimal answers.

**5. Implementation:**
*   A classifier must be created to accurately map incoming user input to the correct system response.

**6. Testing:**
*   Testing must occur in two phases: automated testing and real-life testing with actual users.

**7. Deployment and Revision:**
*   Interactions must be closely monitored post-launch to identify areas for further development and refinement.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[self-wiki/raw/origin-apple-notes/note ai.md]]
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/origin-apple-notes/note ai.md]]