# PR Command

This command helps create standardized pull requests following the project's conventions.

## Usage

Use this command to:
- Create pull requests with consistent formatting
- Follow the project's PR template structure
- Ensure all required information is included
- Maintain code quality standards

## PR Creation Process

1. **Branch Management**
   - Create feature branch from main/preview
   - Ensure branch is up to date with remote
   - Push changes to remote repository

2. **PR Content**
   - Clear, descriptive title
   - Comprehensive summary of changes
   - Link to related issues
   - Test plan and verification steps

3. **Quality Checks**
   - All tests passing
   - Code review requirements met
   - Documentation updated if needed
   - Breaking changes noted

## Integration

- Uses GitHub CLI (`gh`) for PR creation
- Follows `.github/pull_request_template.md` structure
- Integrates with project's CI/CD pipeline
- Supports draft PRs for work in progress

## Best Practices

- Keep PRs focused and atomic
- Include screenshots for UI changes
- Document any breaking changes
- Ensure tests cover new functionality
- Follow conventional commit messages