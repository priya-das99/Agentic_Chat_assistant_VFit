# Requirements Document

## Introduction

This document specifies the requirements for Phase 2 architectural simplification of the chat service. The goal is to remove pre-processing logic from ChatService and let the orchestrator agent handle all routing, shortcuts, multi-turn conversations, and domain filtering naturally. This simplification is expected to reduce the codebase by approximately 500 lines while preserving all existing functionality.

**Key Principle**: The orchestrator agent already has the intelligence to handle these concerns - we're removing redundant pre-processing layers that duplicate this capability.

## Glossary

- **ChatService**: The main service that processes user messages and coordinates responses
- **Orchestrator_Agent**: The main agent (run_main_agent via fitness_agent) that handles all conversation logic
- **Pre_Processing_Logic**: Complex conditional routing in ChatService that happens before calling the orchestrator
- **Flow_Services**: ActivityFlowService and MoodFlowService that manage multi-turn conversation state
- **ShortcutService**: Service that detects and handles quick actions like "log water", "log sleep", "log weight"
- **DomainGuard**: Service that filters out-of-scope messages using keyword matching
- **Multi_Turn_Conversation**: A conversation flow requiring multiple exchanges (e.g., mood logging with reason prompt)

## Requirements

### Requirement 1: Remove Pre-Processing Logic from ChatService

**User Story:** As a developer, I want ChatService to have minimal logic, so that all conversation intelligence lives in the orchestrator agent

#### Acceptance Criteria

1. THE ChatService.process_message method SHALL contain fewer than 100 lines of code
2. THE ChatService SHALL NOT call ShortcutService.normalize_action() before calling the orchestrator
3. THE ChatService SHALL NOT call ShortcutService.handle_pending_shortcut_input() before calling the orchestrator
4. THE ChatService SHALL NOT call ActivityFlowService.resume_from_message() before calling the orchestrator
5. THE ChatService SHALL NOT call MoodFlowService.resume_from_message() before calling the orchestrator
6. THE ChatService SHALL NOT call MoodFlowService.start_from_message() before calling the orchestrator
7. THE ChatService SHALL NOT call DomainGuard.check() before calling the orchestrator
8. THE ChatService SHALL NOT call ActivityService.analyze_activity_message() before calling the orchestrator
9. THE ChatService SHALL NOT call _extract_step_count() before calling the orchestrator
10. THE ChatService SHALL NOT call _is_challenge_query() before calling the orchestrator
11. THE simplified flow SHALL be: save user message → call orchestrator → save assistant response
12. THE ChatService SHALL still initialize user, profile, memories, and session before processing

### Requirement 2: Delete ActivityFlowService

**User Story:** As a developer, I want to remove ActivityFlowService, so that the orchestrator agent handles activity logging flows naturally

#### Acceptance Criteria

1. THE file backend/app/services/activity_flow_service.py SHALL be deleted
2. THE ChatService SHALL NOT import ActivityFlowService
3. THE ChatService SHALL NOT instantiate ActivityFlowService in __init__
4. THE ChatService SHALL NOT call any ActivityFlowService methods
5. THE Orchestrator_Agent SHALL handle activity logging flows through natural conversation
6. THE activity_draft_repository and activity_catalog_repository MAY remain if needed by other services
7. ALL references to ActivityFlowService in imports SHALL be removed

### Requirement 3: Delete MoodFlowService

**User Story:** As a developer, I want to remove MoodFlowService, so that the orchestrator agent handles mood logging flows naturally

#### Acceptance Criteria

1. THE file backend/app/services/mood_flow_service.py SHALL be deleted
2. THE ChatService SHALL NOT import MoodFlowService
3. THE ChatService SHALL NOT instantiate MoodFlowService in __init__
4. THE ChatService SHALL NOT call any MoodFlowService methods
5. THE Orchestrator_Agent SHALL handle mood logging flows through natural conversation
6. THE mood_draft_repository MAY remain if needed by other services
7. ALL references to MoodFlowService in imports SHALL be removed

### Requirement 4: Delete ShortcutService

**User Story:** As a developer, I want to remove ShortcutService, so that the orchestrator agent understands shortcuts naturally

#### Acceptance Criteria

1. THE file backend/app/services/shortcut_service.py SHALL be deleted
2. THE ChatService SHALL NOT import ShortcutService
3. THE ChatService SHALL NOT instantiate ShortcutService in __init__
4. THE ChatService SHALL NOT call any ShortcutService methods
5. THE Orchestrator_Agent SHALL understand "log water", "log sleep", "log weight" commands
6. THE Orchestrator_Agent SHALL handle multi-turn shortcut flows (e.g., asking "how much water?")
7. THE session_shortcut_state_repository MAY remain if needed for state management
8. ALL references to ShortcutService in imports SHALL be removed

### Requirement 5: Delete DomainGuard

**User Story:** As a developer, I want to remove DomainGuard, so that the orchestrator agent handles out-of-scope requests intelligently

#### Acceptance Criteria

1. THE file backend/app/services/domain_guard.py SHALL be deleted
2. THE ChatService SHALL NOT import DomainGuard
3. THE ChatService SHALL NOT instantiate DomainGuard in __init__
4. THE ChatService SHALL NOT call DomainGuard.check()
5. THE Orchestrator_Agent SHALL politely redirect off-topic requests
6. THE Orchestrator_Agent SHALL NOT use brittle keyword matching for domain detection
7. ALL references to DomainGuard in imports SHALL be removed

### Requirement 6: Preserve All User-Facing Functionality

**User Story:** As a user, I want all existing chat functionality to work exactly as before, so that my experience is unchanged

#### Acceptance Criteria

1. WHEN a user sends "log water", THE System SHALL prompt for water amount and log it with cumulative daily totals
2. WHEN a user sends "log sleep", THE System SHALL prompt for sleep hours and log it
3. WHEN a user sends "log weight", THE System SHALL prompt for weight and log it
4. WHEN a user says "I'm feeling happy", THE System SHALL log the mood (with reason prompt if needed)
5. WHEN a user says "I did yoga for 30 minutes", THE System SHALL log the activity
6. WHEN a user sends a step count like "5000 steps", THE System SHALL update challenge progress
7. WHEN a user asks about challenges, THE System SHALL provide challenge status
8. THE System SHALL maintain the same response formats and celebration messages
9. THE System SHALL handle multi-turn flows (e.g., "log water" → "250 ml" → confirmation)
10. THE System SHALL allow users to cancel flows mid-conversation

### Requirement 7: Maintain API Compatibility

**User Story:** As a frontend developer, I want the API to remain unchanged, so that I don't need to modify the frontend

#### Acceptance Criteria

1. THE /chat endpoint signature SHALL remain unchanged
2. THE response format SHALL remain unchanged
3. THE database schema SHALL remain unchanged
4. THE session management behavior SHALL remain unchanged
5. THE get_recent_logs method SHALL remain unchanged

### Requirement 8: Achieve Target Code Reduction

**User Story:** As a developer, I want to reduce the codebase by ~500 lines, so that the system is simpler and easier to maintain

#### Acceptance Criteria

1. THE refactoring SHALL remove approximately 500 lines of code from the services layer
2. THE ChatService.process_message method SHALL be reduced from ~250 lines to fewer than 100 lines
3. THE following files SHALL be deleted:
   - backend/app/services/activity_flow_service.py (~300 lines)
   - backend/app/services/mood_flow_service.py (~200 lines)
   - backend/app/services/shortcut_service.py (~250 lines)
   - backend/app/services/domain_guard.py (~20 lines)
4. THE ChatService SHALL have fewer than 10 conditional branches in process_message
5. THE overall architecture SHALL be simpler with fewer layers

### Requirement 9: Update Tests to Verify Orchestrator Behavior

**User Story:** As a developer, I want tests to verify the new architecture, so that I can ensure correctness

#### Acceptance Criteria

1. THE existing chat flow tests SHALL be updated to test orchestrator behavior
2. THE existing activity logging tests SHALL continue to pass
3. THE existing mood logging tests SHALL continue to pass
4. WHERE tests reference removed services, THE tests SHALL be updated to verify end-to-end behavior
5. THE test coverage SHALL remain at the same level or higher
6. NEW tests MAY be added to verify orchestrator routing logic

### Requirement 10: Orchestrator Agent Capabilities

**User Story:** As a developer, I want the orchestrator agent to have necessary tools and instructions, so that it can handle all routing logic

#### Acceptance Criteria

1. THE Orchestrator_Agent SHALL have access to activity logging tools
2. THE Orchestrator_Agent SHALL have access to mood logging tools
3. THE Orchestrator_Agent SHALL have access to challenge tools
4. THE Orchestrator_Agent SHALL have access to water/sleep/weight logging tools
5. THE Orchestrator_Agent SHALL have instructions for handling shortcuts
6. THE Orchestrator_Agent SHALL have instructions for multi-turn conversations
7. THE Orchestrator_Agent SHALL have instructions for domain filtering
8. THE Orchestrator_Agent SHALL maintain conversation context through session memory
9. WHERE new tools are needed, THE System SHALL create them following existing patterns
10. THE agent instructions SHALL include examples of shortcut flows and multi-turn conversations
