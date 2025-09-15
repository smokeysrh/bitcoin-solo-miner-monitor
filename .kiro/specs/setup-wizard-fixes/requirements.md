# Requirements Document

## Introduction

This feature addresses multiple critical issues and improvements needed for the setup wizard functionality. The setup wizard currently has several UI/UX problems including non-responsive navigation, inconsistent branding, broken visual feedback, and unnecessary complexity that need to be resolved to provide a smooth onboarding experience for users.

## Requirements

### Requirement 1

**User Story:** As a user completing the setup wizard, I want the navigation buttons (continue and back) to be positioned at the bottom of each page content and remain functional, so that I can navigate through the setup process reliably.

#### Acceptance Criteria

1. WHEN a setup wizard page loads THEN the navigation bar with back and continue buttons SHALL be positioned at the bottom of the page content
2. WHEN a user scrolls on a setup wizard page THEN the navigation bar SHALL remain statically positioned at the bottom of the page content and not move with the scroll
3. WHEN a user reaches the bottom of the page by scrolling THEN the navigation bar SHALL be visible and accessible
4. WHEN a user clicks the continue or back buttons THEN they SHALL function properly and navigate to the appropriate step

### Requirement 2

**User Story:** As a user viewing the application, I want all Bitcoin logos to use the consistent, properly centered branding assets, so that the application appears professional and cohesive.

#### Acceptance Criteria

1. WHEN any Bitcoin logo is displayed THEN the system SHALL use the bitcoin-symbol.png or bitcoin-symbol.svg files from the root directory
2. WHEN logos are rendered THEN they SHALL be properly centered and aligned
3. WHEN the application loads THEN no custom-built logos with off-center "B" SHALL be visible

### Requirement 3

**User Story:** As a user selecting dashboard widgets in step 4, I want clear visual feedback showing which widgets I have selected, so that I can make informed choices about my dashboard configuration.

#### Acceptance Criteria

1. WHEN a user clicks on a widget option THEN the system SHALL highlight the selected widget with a distinct visual indicator
2. WHEN a user selects multiple widgets THEN all selected widgets SHALL remain visually highlighted
3. WHEN a user deselects a widget THEN the highlight SHALL be removed immediately

### Requirement 4

**User Story:** As a user interacting with dropdown menus, I want the menu titles to be clearly readable when hovering, so that I can understand my options without visual interference.

#### Acceptance Criteria

1. WHEN a user hovers over a dropdown menu THEN the title text SHALL remain clearly visible
2. WHEN dropdown outlines are displayed THEN they SHALL not obscure or cloud the menu titles
3. WHEN hovering occurs THEN the text contrast SHALL be sufficient for readability

### Requirement 5

**User Story:** As a user selecting chart types, I want a simplified interface that focuses on supported functionality, so that I'm not confused by options that don't work or aren't needed.

#### Acceptance Criteria

1. WHEN chart selection is presented THEN the system SHALL only show line chart options
2. WHEN the chart interface loads THEN no dropdown for multiple chart styles SHALL be displayed
3. WHEN users interact with charts THEN only functional line chart capabilities SHALL be available

### Requirement 6

**User Story:** As a user completing the setup wizard, I want a clean completion page without references to unavailable features, so that I have realistic expectations about the application's current capabilities.

#### Acceptance Criteria

1. WHEN the setup completion page loads THEN no video tutorial references SHALL be displayed
2. WHEN completion content is shown THEN it SHALL only reference actually available features and resources
3. WHEN users view the completion page THEN the content SHALL be focused and relevant

### Requirement 7

**User Story:** As a user finishing the setup wizard, I want the "Launch Dashboard" button to actually take me to the dashboard, so that I can immediately start using the application.

#### Acceptance Criteria

1. WHEN a user clicks the "Launch Dashboard" button THEN the system SHALL navigate to the main dashboard page
2. WHEN navigation occurs THEN the dashboard SHALL load with the user's configured settings
3. WHEN the dashboard loads THEN it SHALL display the widgets selected during setup

### Requirement 8

**User Story:** As a user viewing information bubbles throughout the setup wizard, I want consistent visual styling, so that the interface appears polished and professional.

#### Acceptance Criteria

1. WHEN information bubbles are displayed THEN they SHALL all use the same color scheme as step 3 "settings" info bubble
2. WHEN multiple bubbles appear THEN their styling SHALL be visually consistent
3. WHEN bubbles are rendered THEN they SHALL maintain the established design pattern

### Requirement 9

**User Story:** As a user who wants email notifications, I want a place in settings to configure my email address, so that I can receive notifications at my preferred email.

#### Acceptance Criteria

1. WHEN email notifications are offered during setup THEN there SHALL be a corresponding settings section for email configuration
2. WHEN a user accesses email settings THEN they SHALL be able to enter and save their preferred email address
3. WHEN email settings are saved THEN the system SHALL validate the email format before accepting it

### Requirement 10

**User Story:** As a user customizing the application appearance, I want accent color choices that match the overall theme, so that my customizations look cohesive with the rest of the application.

#### Acceptance Criteria

1. WHEN accent color options are presented THEN they SHALL match the existing color gradients and shades used throughout the application
2. WHEN a user selects an accent color THEN it SHALL integrate seamlessly with the current theme
3. WHEN colors are applied THEN they SHALL maintain proper contrast and accessibility standards

### Requirement 11

**User Story:** As a user progressing through the setup wizard, I want the progress bar to visually indicate my completion status, so that I can track my progress through the setup process.

#### Acceptance Criteria

1. WHEN a user completes a setup step THEN the progress bar SHALL fill with orange color to indicate completion
2. WHEN progress is made THEN the visual indicator SHALL update immediately
3. WHEN the setup wizard loads THEN the progress bar SHALL accurately reflect the current step and completion status