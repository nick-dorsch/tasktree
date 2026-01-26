-- Seed data for testing 3-level dependency graph
-- Level 1 tasks (no dependencies)
INSERT INTO tasks (name, description, status, priority) VALUES
('Setup Database', 'Initialize the database schema', 'completed', 1),
('Install Dependencies', 'Install required npm packages', 'completed', 1),
('Create Project Structure', 'Set up initial project folders and files', 'completed', 1);

-- Level 2 tasks (depend on Level 1 tasks)
INSERT INTO tasks (name, description, status, priority) VALUES
('Design API', 'Design REST API endpoints and data models', 'in_progress', 2),
('Implement Database Layer', 'Create database connection and models', 'in_progress', 2),
('Setup Authentication', 'Implement user authentication system', 'pending', 2);

-- Level 3 tasks (depend on Level 2 tasks)
INSERT INTO tasks (name, description, status, priority) VALUES
('Build User Interface', 'Create frontend components and pages', 'pending', 3),
('Implement Business Logic', 'Add core application logic and validation', 'pending', 3),
('Add Testing Suite', 'Write unit and integration tests', 'pending', 3),
('Deploy Application', 'Deploy to production environment', 'pending', 3);

-- Create dependencies
-- Level 2 -> Level 1 dependencies
INSERT INTO dependencies (task_name, depends_on_task_name) VALUES
-- Design API depends on Setup Database and Create Project Structure
('Design API', 'Setup Database'), ('Design API', 'Create Project Structure'),
-- Implement Database Layer depends on Setup Database and Install Dependencies  
('Implement Database Layer', 'Setup Database'), ('Implement Database Layer', 'Install Dependencies'),
-- Setup Authentication depends on Install Dependencies and Create Project Structure
('Setup Authentication', 'Install Dependencies'), ('Setup Authentication', 'Create Project Structure');

-- Level 3 -> Level 2 dependencies
INSERT INTO dependencies (task_name, depends_on_task_name) VALUES
-- Build User Interface depends on Design API
('Build User Interface', 'Design API'),
-- Implement Business Logic depends on Design API and Implement Database Layer
('Implement Business Logic', 'Design API'), ('Implement Business Logic', 'Implement Database Layer'),
-- Add Testing Suite depends on Implement Database Layer and Setup Authentication
('Add Testing Suite', 'Implement Database Layer'), ('Add Testing Suite', 'Setup Authentication'),
-- Deploy Application depends on all Level 2 tasks
('Deploy Application', 'Design API'), ('Deploy Application', 'Implement Database Layer'), ('Deploy Application', 'Setup Authentication');

-- Create some circular dependency for testing (commented out - uncomment if needed for testing)
-- INSERT INTO dependencies (task_name, depends_on_task_name) VALUES
-- ('Setup Database', 'Deploy Application'); -- This would create a circular dependency
