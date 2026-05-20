---
last_updated: 2024-05-20T12:00:00Z
title: REST Software Architecture Principles
description: A foundational exploration of the constraints and concepts underlying RESTful web services architecture.
tags: [type/principle, work, technology]
---

> This document outlines the core concepts and constraints of RESTful architecture, serving as a technical reference point for designing scalable network-based software. It synthesizes theoretical constraints into practical implementation guidelines.

## Evolution
- Initial draft based on a specific technical review from 2018. The content is being formalized into a principle-based document.

## Content
### REST Architectural Constraints
The REST architectural style, as defined by Fielding, imposes several constraints on services to achieve scalability, simplicity, and uniform interface:

1.  **Client-Server**: Separation of concerns between the client (UI/presentation) and the server (data storage/business logic).
2.  **Statelessness**: Each request from the client to the server must contain all the information needed to understand the request; the server should not rely on session context.
3.  **Cachable**: Responses must explicitly state whether they are cacheable or not to prevent unnecessary requests.
4.  **Uniform Interface**: A standardized way of interacting with the service, typically involving resource identification (URI), manipulation (HTTP methods like GET, POST, PUT, DELETE), and self-descriptive messages.
5.  **Layered System**: The client should not know if it is connected directly to the end server or to an intermediary layer.

### Reference Material
The original source material references the dissertation detailing these constraints.

## Backlinks
<!-- BEGIN BACKLINKS -->
- **Mentioned in**: [[Self_Wiki_Operating_Manual.md]] (Conceptual mapping of structured knowledge)
<!-- END BACKLINKS -->

## Sources
- [[self-wiki/raw/diary/tech/2018-03-04-REST-architecture.md]]